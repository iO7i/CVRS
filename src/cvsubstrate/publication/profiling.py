"""Controller-observed wall time and sampled process memory; no fake phase metrics."""
from pathlib import Path
import time
from cvsubstrate.provenance.io import read_jsonl,write_json
from cvsubstrate.execution.process import run_command
from cvsubstrate.security import sanitize

class ProcessMetrics:
    def __init__(self,gpu=False):
        self.samples=0;self.peak_rss=None;self.cpu={};self.gpu_peak=None;self.errors=[];self.psutil=None;self.nvml=None
        try:import psutil;self.psutil=psutil
        except ImportError:self.errors.append('psutil unavailable: process memory/CPU unobserved')
        if gpu:
            try:
                import pynvml
                pynvml.nvmlInit();self.nvml=pynvml
            except Exception:self.errors.append('NVML unavailable: GPU process memory unobserved')
    def __call__(self,pid,event):
        if self.psutil is None:return
        try:
            root=self.psutil.Process(pid);processes=[root,*root.children(recursive=True)];pids=set();rss=0
            for proc in processes:
                try:
                    pids.add(proc.pid);rss+=proc.memory_info().rss;t=proc.cpu_times()
                    self.cpu[str(proc.pid)]=max(self.cpu.get(str(proc.pid),0),t.user+t.system)
                except (self.psutil.NoSuchProcess,self.psutil.AccessDenied):pass
            self.peak_rss=max(self.peak_rss or 0,rss);self.samples+=1
            if self.nvml:
                used=0;observed=False
                for i in range(self.nvml.nvmlDeviceGetCount()):
                    h=self.nvml.nvmlDeviceGetHandleByIndex(i)
                    for proc in self.nvml.nvmlDeviceGetComputeRunningProcesses(h):
                        memory=getattr(proc,'usedGpuMemory',None)
                        if proc.pid in pids and isinstance(memory,int) and memory<2**63:used+=memory;observed=True
                if observed:self.gpu_peak=max(self.gpu_peak or 0,used)
        except (self.psutil.NoSuchProcess,self.psutil.AccessDenied):pass
        except Exception as exc:
            message='Metrics observation: '+type(exc).__name__
            if message not in self.errors:self.errors.append(message)
    def close(self):
        if self.nvml:
            try:self.nvml.nvmlShutdown()
            except Exception:pass

def phase_durations(path):
    if path is None:return {'status':'UNOBSERVED','phases':{}}
    events=read_jsonl(Path(path));started: dict[str, float]={};durations: dict[str, list[float]]={}
    for event in events:
        phase=event.get('phase');kind=event.get('event');t=event.get('monotonic_seconds')
        if not isinstance(phase,str) or not isinstance(t,(int,float)):raise ValueError('phase event requires phase and monotonic_seconds')
        if kind=='start':
            if phase in started:raise ValueError('duplicate open phase')
            started[phase]=t
        elif kind=='end':
            if phase not in started or t<started[phase]:raise ValueError('unmatched/nonmonotonic phase end')
            durations.setdefault(phase,[]).append(t-started.pop(phase))
        else:raise ValueError('phase event must be start/end')
    return {'status':'PARTIAL' if started else 'OBSERVED','phases':durations,'incomplete':sorted(started)}

def profile_command(argv,destination,*,trust=False,timeout=600,gpu_metrics=False,phase_events=None):
    if not trust:raise ValueError('profiling executes the supplied command; explicit trust required')
    root=Path(destination)
    if root.exists():raise ValueError('new profile output required')
    root.mkdir();start=time.perf_counter();error=None;metrics=ProcessMetrics(gpu_metrics)
    try:
        run_command(argv,timeout,log=root/'process.log',process_observer=metrics);status='SUCCEEDED'
    except Exception as exc:status='FAILED';error={'type':type(exc).__name__,'message':str(exc)}
    finally:metrics.close()
    result={'status':status,'argv':sanitize(argv),'wall_seconds':time.perf_counter()-start,'error':sanitize(error),
        'sampled_peak_process_tree_rss_bytes':metrics.peak_rss,'observed_process_cpu_seconds':sum(metrics.cpu.values()) if metrics.samples else None,
        'sampled_gpu_process_bytes':metrics.gpu_peak,'samples':metrics.samples,'measurement_warnings':metrics.errors,
        'phase_breakdown':phase_durations(phase_events),
        'limits':'Sampled root/descendant RSS is not a hard memory bound or absolute peak. Native phases require explicit events. NVML measurements require opt-in and available hardware.'}
    write_json(root/'profile.json',result);return result
