"""The cvrs CLI. JSON successes on stdout; structured failures on stderr."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import read_json, write_json

def parser():
    p = argparse.ArgumentParser(prog='cvrs', description='Explicit CV experiments with isolated workers and verifiable evidence.')
    p.add_argument('--version', action='version', version='cvrs '+__import__('cvsubstrate').__version__)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('closure',help='Finite v1 closure workflows; closure --help')
    sub.add_parser('doctor', help='Inspect this interpreter without importing ML frameworks or downloading models')
    a = sub.add_parser('capabilities')
    a.add_argument('--adapter', choices=['native_torch', 'mmdetection', 'ultralytics', 'rfdetr'], default='native_torch')
    a.add_argument('--worker-python')
    a = sub.add_parser('fixtures')
    a.add_argument('destination', type=Path)
    a = sub.add_parser('schemas')
    a.add_argument('destination', type=Path)
    a = sub.add_parser('dataset')
    a.add_argument('action', choices=['validate'])
    a.add_argument('manifest', type=Path)
    a.add_argument('--metadata-only', action='store_true')
    a = sub.add_parser('experiment')
    a.add_argument('action', choices=['validate'])
    a.add_argument('spec', type=Path)
    a = sub.add_parser('run')
    a.add_argument('spec', type=Path)
    a.add_argument('--out', type=Path, default=Path('runs'))
    a.add_argument('--worker-python')
    a.add_argument('--timeout', type=float, default=180.0)
    a.add_argument('--authorization', type=Path)
    a.add_argument('--evaluator-python')
    a = sub.add_parser('evaluate')
    a.add_argument('--evaluator-python')
    a.add_argument('predictions', type=Path)
    a.add_argument('--dataset', type=Path, required=True)
    a.add_argument('--split', default='dev')
    a.add_argument('--protocol', type=Path, required=True)
    a.add_argument('--out', type=Path)
    a = sub.add_parser('compare')
    a.add_argument('left', type=Path)
    a.add_argument('right', type=Path)
    a = sub.add_parser('verify')
    a.add_argument('run', type=Path)
    a.add_argument('--dataset', type=Path)
    a = sub.add_parser('report')
    a.add_argument('run', type=Path)
    a = sub.add_parser('heritage')
    a.add_argument('action', choices=['inspect', 'inspect-config', 'adapter', 'certify'])
    a.add_argument('reference', type=Path)
    a.add_argument('--run', type=Path)
    a.add_argument('--out', type=Path)
    a.add_argument('--tolerance', type=float, default=1e-6)
    a = sub.add_parser('reference-parity')
    a.add_argument('predictions', type=Path)
    a.add_argument('--dataset', type=Path, required=True)
    a.add_argument('--split', default='dev')
    a.add_argument('--protocol', type=Path, required=True)
    a.add_argument('--tolerance', type=float, default=1e-6)
    a.add_argument('--out', type=Path)
    a = sub.add_parser('native-coco-evaluate', help='Evaluate preserved COCO artifacts without canonical geometry rewriting')
    a.add_argument('annotations', type=Path)
    a.add_argument('detections', type=Path)
    a.add_argument('--protocol', type=Path)
    a.add_argument('--image-id', type=int, action='append', dest='image_ids')
    a.add_argument('--out', type=Path)
    a = sub.add_parser('cross-compare')
    a.add_argument('left', type=Path)
    a.add_argument('right', type=Path)
    a.add_argument('--out', type=Path)
    a = sub.add_parser('protocol')
    a.add_argument('action', choices=['plan'])
    a.add_argument('spec', type=Path)
    a.add_argument('--out', type=Path)
    a = sub.add_parser('import-coco')
    a.add_argument('annotations', type=Path)
    a.add_argument('--image-root', type=Path, required=True)
    a.add_argument('--name', required=True)
    a.add_argument('--role', choices=['train', 'dev', 'selection', 'locked_test'], default='dev')
    a.add_argument('--source', choices=['real', 'synthetic', 'unknown'], default='unknown')
    a.add_argument('--out', type=Path, required=True)
    a = sub.add_parser('demo')
    a.add_argument('destination', type=Path)
    a.add_argument('--worker-python')
    a.add_argument('--timeout', type=float, default=180.0)
    from cvsubstrate.cli_frontier import ROOTS as FRONTIER_ROOTS
    for name in sorted(FRONTIER_ROOTS):sub.add_parser(name,help='0.5 closure/vision/registry; use '+name+' --help')
    from cvsubstrate.cli_groundwork import ROOTS
    for name in sorted(ROOTS):
        sub.add_parser(name,help='0.4 groundwork command; use '+name+' --help')
    p.epilog='New nested commands: dataset import/materialize; heritage import/catalogue/profiles; campaign compile/run-stages/sweep; capsule create/materialize; report create. Legacy forms remain available.'
    from cvsubstrate.cli_research import add_commands
    add_commands(sub)
    return p

def save_derived(path, value):
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
    assert_not_inside_sealed(path)
    if Path(path).exists():
        raise CVRSError('OUTPUT_EXISTS', 'derived JSON must not overwrite existing evidence')
    write_json(path, value)

def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))

def main(argv=None):
    values=list(sys.argv[1:] if argv is None else argv)
    from cvsubstrate.cli_product import handles as product_handles, main as product_main
    if product_handles(values):return product_main(values)
    from cvsubstrate.cli_adoption import handles as adoption_handles, main as adoption_main
    if adoption_handles(values):return adoption_main(values)
    if values and values[0]=='closure':
        from cvsubstrate.cli_closure import main as closure_main
        return closure_main(values[1:])
    argv=list(sys.argv[1:] if argv is None else argv)
    from cvsubstrate.cli_frontier import handles as frontier_handles,main as frontier_main
    if frontier_handles(argv):return frontier_main(argv)
    from cvsubstrate.cli_groundwork import handles,main as groundwork_main
    if handles(argv):return groundwork_main(argv)
    if argv in (['--help'], ['-h']):
        print(parser().format_help())
        from cvsubstrate.cli_adoption import parser as adoption_parser
        print('\nSlice 6 adoption / publication commands:\n'+adoption_parser().format_help())
        from cvsubstrate.cli_product import parser as product_parser
        print('\nManaged product / release workflows:\n'+product_parser().format_help())
        return 0
    args = parser().parse_args(argv)
    try:
        if args.command == 'doctor':
            from cvsubstrate.provenance.bundle import environment_snapshot
            result = environment_snapshot()
            result['capabilities'] = {m: {'installed': importlib.util.find_spec(m) is not None, 'execution_verified': False} for m in ['torch', 'torchvision', 'pycocotools', 'mmdet']}
            result['note'] = 'Presence is not execution verification. No downloads or training performed.'
        elif args.command == 'capabilities':
            from cvsubstrate.contracts.models import WorkerRequest
            from cvsubstrate.execution.process import invoke
            result = invoke(args.adapter, WorkerRequest(operation='capabilities'), args.worker_python, 45).result
        elif args.command == 'fixtures':
            from cvsubstrate.data.fixtures import generate
            result = generate(args.destination)
        elif args.command == 'schemas':
            from cvsubstrate.schemas.registry import export_schemas
            result=export_schemas(args.destination)
        elif args.command == 'dataset':
            from cvsubstrate.contracts.models import DatasetManifest
            from cvsubstrate.data.manifest import validate_manifest
            result = validate_manifest(DatasetManifest.model_validate(read_json(args.manifest)), args.manifest.resolve().parent, not args.metadata_only)
        elif args.command == 'experiment':
            from cvsubstrate.execution.runner import load_experiment
            from cvsubstrate.provenance.io import experiment_identity
            spec, m, path = load_experiment(args.spec)
            result = {'status': 'VALID', 'experiment_digest': experiment_identity(spec), 'dataset_digest': spec.dataset_sha256, 'backend_execution_verified': False}
        elif args.command == 'run':
            from cvsubstrate.execution.runner import run_experiment
            authorization = read_json(args.authorization) if args.authorization else None
            result = {'run': str(run_experiment(args.spec, args.out, args.worker_python, args.timeout, authorization,evaluator_python=args.evaluator_python)), 'status': 'SUCCEEDED'}
        elif args.command == 'evaluate':
            from cvsubstrate.contracts.models import DetectionPrediction, EvaluationProtocol
            from cvsubstrate.data.manifest import load_manifest
            from cvsubstrate.evaluation.metrics import evaluate
            from cvsubstrate.provenance.io import read_jsonl
            m = load_manifest(args.dataset)
            if args.split not in m.splits or m.splits[args.split].role != 'dev':
                raise CVRSError('EVAL_ROLE', 'standalone evaluation accepts dev only; locked_test requires an authorized final run')
            path = args.predictions / 'predictions.jsonl' if args.predictions.is_dir() else args.predictions
            rows = [DetectionPrediction.model_validate(r) for r in read_jsonl(path)]
            if args.evaluator_python:
                from cvsubstrate.evaluation.service import evaluate_isolated
                result=evaluate_isolated(m,args.split,rows,EvaluationProtocol.model_validate(read_json(args.protocol)),worker_python=args.evaluator_python)
            else:result = evaluate(m, args.split, rows, EvaluationProtocol.model_validate(read_json(args.protocol)))
            if args.out:
                if args.out.exists():
                    raise CVRSError('OUTPUT_EXISTS', 'refusing to overwrite existing evaluation artifact')
                save_derived(args.out, result)
        elif args.command == 'compare':
            from cvsubstrate.evaluation.compare import compare

            def metrics(p):
                return read_json(p / 'metrics.json' if p.is_dir() else p)
            result = compare(metrics(args.left), metrics(args.right))
        elif args.command == 'verify':
            from cvsubstrate.provenance.bundle import verify_bundle
            result = verify_bundle(args.run, args.dataset)
            emit(result)
            return 0 if result['status'] == 'VERIFIED' else 2
        elif args.command == 'report':
            from cvsubstrate.provenance.bundle import verify_bundle
            v = verify_bundle(args.run)
            if v['status'] != 'VERIFIED':
                raise CVRSError('EVIDENCE_INVALID', 'verify bundle before reading report')
            text = (args.run / 'report.md').read_text('utf-8')
            print(text)
            return 0
        elif args.command == 'heritage':
            from cvsubstrate.execution.heritage import inspect_reference, inspect_config, adapter_fragment, certify_run
            if args.action == 'inspect':
                result = inspect_reference(args.reference)
            elif args.action == 'inspect-config':
                result = inspect_config(args.reference)
            elif args.action == 'adapter':
                result = adapter_fragment(args.reference)
            else:
                if args.run is None:
                    raise CVRSError('RUN_REQUIRED', 'heritage certify requires --run')
                result = certify_run(args.run, args.reference, args.tolerance, args.out)
        elif args.command == 'reference-parity':
            from cvsubstrate.contracts.models import DetectionPrediction, EvaluationProtocol
            from cvsubstrate.data.manifest import load_manifest
            from cvsubstrate.evaluation.reference_coco import parity_report
            from cvsubstrate.provenance.io import read_jsonl
            m = load_manifest(args.dataset)
            path = args.predictions / 'predictions.jsonl' if args.predictions.is_dir() else args.predictions
            rows = [DetectionPrediction.model_validate(r) for r in read_jsonl(path)]
            result = parity_report(m, args.split, rows, EvaluationProtocol.model_validate(read_json(args.protocol)), args.tolerance)
            if args.out:
                save_derived(args.out, result)
        elif args.command == 'native-coco-evaluate':
            from cvsubstrate.contracts.models import EvaluationProtocol
            from cvsubstrate.evaluation.native_coco import evaluate_native_coco
            protocol = EvaluationProtocol.model_validate(read_json(args.protocol)) if args.protocol else None
            result = evaluate_native_coco(args.annotations, args.detections, protocol=protocol, image_ids=args.image_ids)
            if args.out:
                save_derived(args.out, result)
        elif args.command == 'cross-compare':
            from cvsubstrate.evaluation.cross_framework import compare_runs
            result = compare_runs(args.left, args.right)
            if args.out:
                save_derived(args.out, result)
        elif args.command == 'protocol':
            from cvsubstrate.execution.runner import load_experiment
            from cvsubstrate.protocols.planner import plan
            spec, m, path = load_experiment(args.spec)
            result = plan(spec, m)
            if args.out:
                save_derived(args.out, result)
        elif args.command == 'import-coco':
            from cvsubstrate.data.coco import import_coco
            # The manifest uses paths rooted beside it, so require colocating it
            # with the declared image root instead of emitting broken paths.
            if args.out.resolve().parent != args.image_root.resolve():
                raise CVRSError('MANIFEST_ROOT', 'place imported manifest in image-root; all image paths remain relative to it')
            if args.out.exists():
                raise CVRSError('OUTPUT_EXISTS', 'refusing to overwrite manifest')
            m = import_coco(args.annotations, args.image_root, args.name, args.role, args.source)
            write_json(args.out, m)
            result = {'manifest': str(args.out), 'samples': len(m.samples), 'license': 'unknown until supplied by owner'}
        elif args.command == 'demo':
            from cvsubstrate.data.fixtures import generate
            from cvsubstrate.execution.runner import run_experiment
            from cvsubstrate.provenance.bundle import verify_bundle
            if args.destination.exists() and any(args.destination.iterdir()):
                raise CVRSError('OUTPUT_EXISTS', 'demo directory must be absent or empty')
            generate(args.destination / 'fixtures')
            run = run_experiment(args.destination / 'fixtures' / 'real.json', args.destination / 'runs', args.worker_python, args.timeout)
            result = {'run': str(run), 'verification': verify_bundle(run, args.destination / 'fixtures' / 'dataset.json'), 'scope': 'real Faster R-CNN execution on procedural fixtures; diagnostics, NOT COCO AP'}
        else:
            from cvsubstrate.cli_research import dispatch
            result = dispatch(args)
        emit(result)
        return 2 if isinstance(result,dict) and result.get('status') in {'FAILED','FAIL','MISMATCH','INVALID'} else 0
    except (CVRSError, ValueError, OSError, KeyError) as exc:
        from cvsubstrate.errors import public_error
        value = public_error(exc)
        print(json.dumps({'status': 'FAILED', 'error': value}, ensure_ascii=False), file=sys.stderr)
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
