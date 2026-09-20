# Workstations and HPC

```bash
cvrs env scaffold mmdetection3 mm-env --pins known-working-pins.json
cvrs env hpc paper.json --out job.slurm --scheduler slurm --cpus 8 --memory-gb 32 --gpus 1
```

Scaffolding creates declarations, not a solved/transitively locked environment. Empty pins are explicitly incomplete. CUDA/MMCV binary compatibility must be taken from the native project and your hardware.

The HPC generator writes Slurm, PBS or LSF scripts without submitting a job. Configure shared paths and `CVRS_OUTPUT`; use a new result directory. Optional Apptainer wrapping is explicit. Docker and Apptainer definitions never claim to have been built here.

## Windows

Core commands use pathlib and argument lists, not Bash string evaluation. Use `python tools/dev.py` instead of Make. PowerShell paths containing spaces remain individual argv tokens in job JSON. Bash batch scripts are for their named HPC environment, not Windows shell commands.
