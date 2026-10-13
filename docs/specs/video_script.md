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
| 3:05–3:40 | Terminal: `rocm-smi` during benchmark, latency/tokens-per-second table | "Served with vLLM on AMD Developer Cloud. Here are real measurements: p50, p95 latency and tokens per second." |
| 3:40–3:55 | Kill the LLM endpoint; banner flips to REPLAY/TEMPLATE; app keeps working | "If the model goes down, the rules, margin math and audit log keep running." |
| 3:55–4:10 | Recovered-margin counter vs baseline, repo URL, demo URL | "On our synthetic set, recovered margin versus refund-everything is shown here. Numbers are illustrative. Code and live demo are linked below." |

## Recording checklist
- [ ] Mode banner visible in every LLM shot
- [ ] Real benchmark numbers copied from docs/benchmarks/, not retyped from memory
- [ ] Synthetic-data disclosure shown on screen once
- [ ] No keys or tokens visible in terminal or browser
- [ ] Exported as MP4; watched fully before upload
