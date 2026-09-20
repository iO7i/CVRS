import json
import sqlite3
from dataclasses import replace
from pathlib import Path
import pytest
np = pytest.importorskip("numpy")
from cvsubstrate.provenance.io import file_digest
from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger,observe_optimizer
from cvsubstrate.telemetry import summarize_telemetry,aggregate_telemetry
from cvsubstrate.streaming.raster import StreamSpec,Tile,PredictionDatabase,execute_stream,plan_tiles

def test_ledger_counts_steps_repeats_unknown_resume_and_tamper(tmp_path):
    path=tmp_path/'ledger.db';mapping={'a':{'sample_id':'a','source':'real'},'b':{'sample_id':'b','source':'synthetic'}}
    led=TrainingLedger(path,run_id='test',source_map=mapping,mixing_policy='disabled_or_fully_traced')
    led.batch(['a','b','a']);led.optimizer();v=led.summary()
    assert v['source_exposures']=={'real':2,'synthetic':1,'unknown':0} and v['repeat_exposures']==1 and v['source_accounting']=='OBSERVED'
    led.close();v=summarize_telemetry(path);assert v['optimizer_step_calls']==1
    led=TrainingLedger(path,run_id='test',source_map=mapping,mixing_policy='disabled_or_fully_traced',resume=True)
    led.batch(['missing']);assert led.summary()['source_accounting']=='PARTIAL';led.close()
    db=sqlite3.connect(path);db.execute('UPDATE events SET payload=? WHERE seq=0',('{}',));db.commit();db.close()
    with pytest.raises(ValueError):summarize_telemetry(path)

def test_optimizer_hook_real_cpu_and_gradient_accumulation(tmp_path):
    pytest.importorskip('torch')
    import torch
    torch.set_num_threads(1);model=torch.nn.Linear(2,1);opt=torch.optim.SGD(model.parameters(),lr=.1)
    led=TrainingLedger(tmp_path/'x.db',run_id='cpu',source_map={'a':'real'},mixing_policy='disabled_or_fully_traced')
    with observe_optimizer(opt,led):
        for i in range(4):
            led.batch(['a']);model(torch.ones(1,2)).sum().backward()
            if i%2:opt.step();opt.zero_grad()
    s=led.summary();assert s['model_batches']==4 and s['optimizer_step_calls']==2 and s['source_exposures']['real']==4
    opt.step();assert led.summary()['optimizer_step_calls']==2;led.close()

def test_rank_aggregation_requires_complete_identity(tmp_path):
    paths=[]
    for rank in range(2):
        p=tmp_path/str(rank);led=TrainingLedger(p,run_id='run',rank=rank,source_map={'a':'real'},mixing_policy='disabled_or_fully_traced');led.batch(['a']);led.optimizer();led.close();paths.append(p)
    v=aggregate_telemetry(paths,[0,1]);assert v['global_sample_exposures']['real']==2 and v['synchronized_updates']==1
    with pytest.raises(ValueError):aggregate_telemetry(paths,[0,1,2])

def test_disk_nms_future_high_score_classwise(tmp_path):
    s=StreamSpec(raster='x',raster_sha256='a'*64,tile_width=32,tile_height=32,overlap=4,model_identity='x')
    db=PredictionDatabase(tmp_path/'p.db','identity')
    t=Tile('a',1,0,0,32,32,32,32)
    db.write(t,{'boxes':[[1,1,10,10]],'scores':[.1],'category_ids':[0]},.01,s)
    db.write(replace(t,id='b'),{'boxes':[[1,1,10,10],[1,1,10,10]],'scores':[.9,.8],'category_ids':[0,1]},.01,s)
    assert db.merge(.5)==2
    values=list(db.db.execute('SELECT score,category FROM selected ORDER BY score DESC'));assert values==[(.9,0),(.8,1)]
    db.export(tmp_path/'pred.jsonl');assert len((tmp_path/'pred.jsonl').read_text().splitlines())==2;db.close()

def make_raster(path):
    rio=pytest.importorskip('rasterio');from rasterio.transform import from_origin
    with rio.open(path,'w',driver='GTiff',width=130,height=90,count=3,dtype='uint8',crs='EPSG:32637',transform=from_origin(400000,2500000,.5,.5)) as ds:ds.write(np.ones((3,90,130),dtype=np.uint8)*99)
    return path

def test_stream_resumes_real_raster_io_with_analytic_fixture_predictor(tmp_path):
    p=make_raster(tmp_path/'image.tif')
    s=StreamSpec(raster=str(p),raster_sha256=file_digest(p),tile_width=48,tile_height=48,overlap=8,scales=(1.,.5),batch_size=2,model_identity='ANALYTICAL_FIXTURE_NOT_MODEL')
    calls=[]
    def predict(images):
        calls.append(len(images));return [{'boxes':[[0.,0.,float(im.shape[1]),float(im.shape[0])]],'scores':[.5],'category_ids':[0]} for im in images]
    first=execute_stream(s,predict,tmp_path/'out',max_tiles=3);assert first['status']=='PARTIAL' and first['committed_tiles']==3
    second=execute_stream(s,predict,tmp_path/'out',resume=True);assert second['status']=='SUCCEEDED' and second['reused_tiles']==3
    assert max(calls)<=2 and second['peak_batch_array_bytes']<=2*48*48*4
    with pytest.raises(ValueError):execute_stream(replace(s,model_identity='changed'),predict,tmp_path/'out',resume=True)
    assert next(plan_tiles(100000,100000,replace(s,scales=(1.,)))).id=='0:0:0'

def test_stream_budgets_and_malformed_native_output(tmp_path):
    s=StreamSpec(raster='x',raster_sha256='a'*64,model_identity='fixture',working_memory_bytes=10)
    with pytest.raises(ValueError):s.validate()
    p=make_raster(tmp_path/'image.tif');s=replace(s,raster=str(p),raster_sha256=file_digest(p),tile_width=32,tile_height=32,overlap=4,working_memory_bytes=128*1024*1024)
    with pytest.raises(ValueError):execute_stream(s,lambda ims:[{'boxes':[[0.,0.,999.,999.]],'scores':[1.],'category_ids':[0]} for _ in ims],tmp_path/'failed')
    assert (tmp_path/'failed/failure.json').exists()


def test_disk_nms_equal_scores_do_not_depend_on_arrival_order(tmp_path):
    spec=StreamSpec(raster='x',raster_sha256='a'*64,tile_width=32,tile_height=32,overlap=4,model_identity='fixture')
    exports=[]
    for k,order in enumerate([['tile-b','tile-a'],['tile-a','tile-b']]):
        db=PredictionDatabase(tmp_path/f'{k}.sqlite','identity')
        for tid in order:
            t=Tile(tid,1,0,0,32,32,32,32)
            offset=0 if tid=='tile-a' else 1
            db.write(t,{'boxes':[[1+offset,1,10+offset,10]],'scores':[.5],'category_ids':[0]},.01,spec)
        db.merge(.5);db.export(tmp_path/f'{k}.jsonl');db.close()
        exports.append((tmp_path/f'{k}.jsonl').read_bytes())
    assert exports[0]==exports[1]

def test_worker_error_codes_are_stable_not_url_or_validation_messages():
    from cvsubstrate.worker_shims.runtime_common import error_code
    assert error_code(ValueError('3 errors: see https://some-documentation'))=='VALIDATION_ERROR'
    assert error_code(RuntimeError('MODEL_IDENTITY: changed'))=='MODEL_IDENTITY'
    assert error_code(ImportError('missing module'))=='DEPENDENCY_UNAVAILABLE'

