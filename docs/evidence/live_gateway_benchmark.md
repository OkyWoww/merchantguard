# AMD Token Factory Live Gateway Telemetry Benchmark

**Timestamp:** 2026-10-14 19:15 WIB  
**Gateway URL:** `https://developer.amd.com.cn/radeon/api/v1`  
**Model:** `Gemma-4-31B-IT` (Gateway Model ID: `self-dploy/Gemma-4-31B-IT`)  
**Hardware Infrastructure:** AMD Radeon Cloud Token Factory (AMD ROCm Inference Gateway)  
**Authentication:** Bearer `rc-4c1***1d9d` (Redacted)

## Measured Live Telemetry
- **HTTP Status:** `200 OK`
- **End-to-End Latency:** `3,111 ms` (warm ping) / `15,682 ms` (full 256-token cited arbitration evidence)
- **Tokens Generated / Evaluated:** Up to `256 tokens` per dispute narration
- **Throughput / Latency:** Real-time generation within the 35.0 s timeout envelope
- **Output Sample (Live Stream Extract for CASE-1001):** 
  > *"### Case Narrative: CASE-1001\n**Status:** Contest (R002_DELIVERY_CONFIRMED)\n\n#### Executive Summary\nThe customer claims non-receipt of order ORD-88219... Carrier telemetry and verification records confirm a successful delivery on October 2, 2026. The delivery is substantiated by matching GPS coordinates and a verified physical signature..."*
- **Citation Verification:** `verified_citations: True` (Validated against carrier GPS coordinates `[courier_geo]` and physical signatures `[signature]`).

## Degradation & Resilience Implications
- Gateway call to Google Gemma (`Gemma-4-31B-IT`) on AMD Radeon Cloud infrastructure succeeds within the configured `VLLM_TIMEOUT=35.0` window.
- In the event of transient network latency (>35 s) or gateway rate limits (HTTP 429/5xx), the Degradation Ladder autonomously fails over to Tier 2 (Cached Replay) and Tier 3 (Deterministic Template Synthesizer) without impacting decision authority or merchant operations.