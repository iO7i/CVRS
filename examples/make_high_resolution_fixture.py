"""Create a 2048x1536 procedural image to exercise real tiled model execution.

This is NOT an aerial dataset or a detector-quality benchmark. No downloads.
Usage: python examples/make_high_resolution_fixture.py output-directory
       cvrs run-tiled output-directory/inference.json --policy output-directory/tiling.json --out large-image-runs
"""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw
from cvsubstrate.contracts.models import Category,Sample,Box,Split,DatasetManifest,ExperimentSpec,EvaluationProtocol
from cvsubstrate.contracts.research import TilingPolicy
from cvsubstrate.provenance.io import file_digest,digest,write_json


def generate(output:Path):
    if output.exists():raise ValueError('output directory must be new')
    output.mkdir(parents=True)
    image=Image.new('RGB',(2048,1536),(70,85,90));draw=ImageDraw.Draw(image)
    rectangles=[[20.,30.,31.,39.],[510.,505.,523.,516.],[1800.,1400.,1812.,1408.]]
    for b in rectangles:draw.rectangle([b[0],b[1],b[2]-1,b[3]-1],fill=(225,225,220))
    image.save(output/'source.png')
    sample=Sample(id='highres-fixture',image='source.png',sha256=file_digest(output/'source.png'),width=2048,height=1536,source_kind='synthetic',domain='procedural-fixture',boxes=[Box(xyxy=b,category_id=1) for b in rectangles])
    m=DatasetManifest(name='highres-pipeline-fixture',version='1',categories=[Category(id=1,name='fixture-object')],samples=[sample],splits={'dev':Split(role='dev',sample_ids=[sample.id])},purpose='software_fixture',notes='Procedural rectangular objects, not vehicles or aerial imagery. Pipeline correctness only.')
    spec=ExperimentSpec(name='highres-cpu-tiling',dataset='dataset.json',dataset_sha256=digest(m),eval_split='dev',evaluation=EvaluationProtocol(evaluator='diagnostic_detection',evaluator_version='1'))
    policy=TilingPolicy(width=512,height=512,overlap_x=128,overlap_y=128,max_tiles=100)
    write_json(output/'dataset.json',m);write_json(output/'inference.json',spec);write_json(output/'tiling.json',policy)
    return {'width':sample.width,'height':sample.height,'software_fixture':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();print(generate(a.out))
