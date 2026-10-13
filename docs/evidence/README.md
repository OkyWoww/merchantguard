# Evidence & Benchmark Logs

This directory contains benchmark captures, rocm-smi telemetry logs, and throughput logs from AMD ROCm vLLM testing on AMD hardware (MI300X / RX 7900 XTX).

### Captures Checklist:
- `rocm-smi-baseline.log`: GPU memory and compute utilization before inference load
- `rocm-smi-vllm-peak.log`: GPU utilization during batch generation
- `throughput-benchmark.json`: Tokens per second and latency percentiles (p50, p95, p99)
- `degradation-telemetry.log`: Proof of fallback to replay cache when server is offline
