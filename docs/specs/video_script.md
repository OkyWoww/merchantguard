# video_script.md — ~4 minute demo video

Format: screen recording + voiceover, MP4. Keep every claim consistent with README (synthetic data, illustrative numbers).

| Time | Visual | Voiceover |
|---|---|---|
| 0:00–0:25 | Title card, then a spreadsheet of messy disputes | "Merchants lose margin on disputes: they refund winnable cases and fight cases that cost more than they recover. MerchantGuard fixes the decision, not just the wording." |
| 0:25–0:55 | Architecture diagram (gate → margin → LLM → human) | "Rules and a statistical model decide. An open model on AMD infrastructure only writes the cited evidence. The model can never change the decision." |
| 0:55–1:35 | Scenario 1: clean win, SSE streaming, recommended CONTEST, citation chips | "Delivered with signature three days ago. The gate confirms delivery, the model estimates P(win), and the narrative cites each courier fact." |
| 1:35–2:05 | Scenario 3: window bypass auto-rejected, "no LLM call" indicator | "Day 35 on a 14-day policy: rejected by rules instantly, zero tokens spent." |
| 2:05–2:35 | Scenario 4: economic trap, ACCEPT_REFUND with formula expander | "Here the dispute fee exceeds the recoverable margin. Fighting would lose money, so the system recommends refunding." |
| 2:35–3:05 | Scenario 2: ambiguous evidence → NEEDS_HUMAN, approve and log, audit chain verify | "When evidence conflicts, it hands off to a person and records every step in a tamper-evident log." |
| 3:05–3:40 | Split screen: (left) browser Network tab or terminal showing the live `/chat/completions` request to `developer.amd.com.cn` — HTTP 200, model `self-dploy/DeepSeek-V4-Flash`; (right) latency readout and token count from the router log. Optionally: Token Factory portal usage dashboard screenshot. | "Narrative generation runs on AMD infrastructure via the AMD Token Factory gateway — model DeepSeek-V4-Flash, latency under 10 seconds end-to-end on this call, 31 tokens out. Every call is logged with mode, model, latency, and token count in the audit chain. You can see the request hit the AMD endpoint and come back live here." |
| 3:40–3:55 | Kill the LLM endpoint (set LLM_MODE=replay or block the URL); banner flips to REPLAY then TEMPLATE; app keeps working | "If the AMD endpoint goes down, the rules, margin math and audit log keep running — the degradation ladder is a feature, not a fallback. Here it is in real time." |
| 3:55–4:10 | Recovered-margin counter vs baseline, repo URL, demo URL | "On our synthetic set, recovered margin versus refund-everything is shown here. Numbers are illustrative. Code and live demo are linked below." |

## Recording checklist
- [ ] Mode banner visible in every LLM shot (LIVE green / REPLAY blue / TEMPLATE amber)
- [ ] Tier 1 LIVE segment (3:05–3:40) shows actual HTTP 200 response from `developer.amd.com.cn` with model `self-dploy/DeepSeek-V4-Flash` and real latency/token figures — **not** a REPLAY playback
- [ ] Token Factory portal usage screenshot captured and included (or shown on screen during 3:05–3:40)
- [ ] Latency and token count in the video match values in `docs/evidence/` (do not retype from memory)
- [ ] Synthetic-data disclosure shown on screen once
- [ ] No API keys, bearer tokens, or Authorization headers visible in any terminal or browser shot — redact or crop before recording
- [ ] Degradation ladder demo (3:40–3:55) shows both REPLAY and TEMPLATE banners
- [ ] Exported as MP4; watched fully before upload
