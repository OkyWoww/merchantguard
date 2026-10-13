# AMD Token Factory Live Gateway Telemetry Benchmark

**Timestamp:** 2026-10-13 21:07 WIB  
**Gateway URL:** `https://developer.amd.com.cn/radeon/api/v1`  
**Model:** `DeepSeek-V4-Flash` (AMD Radeon Cloud Token Factory)  
**Authentication:** Bearer `rc-4c1***1d9d` (Redacted)

## Measured Live Telemetry
- **HTTP Status:** `200 OK`
- **End-to-End Latency:** `12.89 s` (12,890 ms)
- **Tokens Generated / Evaluated:** `93 tokens`
- **Effective Throughput:** `7.21 tokens/sec`
- **Output Sample:** 
  > *"Defense for CASE-1001: The signed courier note, timestamped and bearing the recipient's signature, conclusively verifies delivery..."*

## Degradation & Resilience Implications
- Gateway call succeeds well within the updated `VLLM_TIMEOUT=35.0` window.
- If network jitter exceeds 35s or returns HTTP 429 / 5xx, the Degradation Ladder cleanly drops to Tier 2 (Replay) and Tier 3 (Deterministic Template) without disruption.