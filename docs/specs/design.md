# design.md — UX & interaction design

## 1. Principles
1. Decision first, narrative second. The recommended action and margin number are the first thing seen.
2. Always show where the answer came from: rule, model, or LLM, and which mode (LIVE / REPLAY / TEMPLATE).
3. One screen, one flow: queue → case → approve.

## 2. Layout
```
┌───────────────────────────────────────────────────────────────┐
│ MerchantGuard      Recovered margin: $X,XXX    Mode: ● LIVE   │
├───────────────┬───────────────────────────────────────────────┤
│ CASE QUEUE    │ CASE #1042   [Urgent]                          │
│ ▸ #1042 Urgent│ ┌ Buyer claim ──────┐ ┌ Courier telemetry ───┐ │
│ ▸ #1038 High  │ │ "never arrived"   │ │ Delivered 3d ago     │ │
│ ▸ #1031 Low   │ │ reason: INR       │ │ signature ✓ geo ✓    │ │
│               │ └───────────────────┘ └──────────────────────┘ │
│ Filters:      │ Policy Gate: DELIVERY_CONFIRMED (R-002)        │
│ Urgent/High/  │ P(win) 82% (synthetic)  Recovery +$46          │
│ Low margin    │ Recommended: CONTEST                           │
│               │ ┌ Evidence narrative (citations [F3][F7]) ───┐ │
│               │ └────────────────────────────────────────────┘ │
│               │ [Edit draft]  [Reject]  [Approve & Log]        │
└───────────────┴───────────────────────────────────────────────┘
```

## 3. Components
- **Queue:** sorted by urgency (deadline) then expected margin impact; badges for status.
- **Compare panel:** buyer claim vs courier events, contradictions highlighted.
- **Decision card:** gate status + rule ID, P(win), expected loss per option, recommendation, a "why" expander showing the formula inputs.
- **Narrative card:** streamed via SSE; each citation chip click highlights its source fact.
- **Action bar:** Approve & Log, Edit, Reject; writes audit record.
- **Mode banner:** LIVE (green), REPLAY (blue, "cached model responses"), TEMPLATE (amber, "LLM unavailable – template narrative").
- **Metrics strip:** recovered margin vs refund-everything baseline, avg decision time.

## 4. States
Loading (skeleton + SSE progress: Gate → Margin → Narrative), LLM-down (narrative shows template text, banner shows REPLAY or TEMPLATE), validation-failed (template narrative + note), empty queue, error toast.

## 5. Visual & accessibility
Dark-on-light neutral palette; semantic colors only for status (green contest / amber partial / red accept / gray needs-human). Do not rely on color alone: icon + text label. Keyboard-operable action bar, contrast ≥ 4.5:1, responsive down to laptop width (mobile not required).

## 6. SSE event shapes
`gate` {status, rule_id, reason} → `margin` {p_win, options[], action} → `narrative_chunk` {text} → `narrative_done` {claims[], mode} → `error` {code}

## 7. Engine status indicator (top-right, always visible)
Shows the real runtime state, never hard-coded text. Example: `Engine: vLLM @ <detected GPU name> (LIVE) | Model: <model id> | P(win): synthetic-trained`.
- GPU/hardware string comes from the serving endpoint or a captured `rocm-smi` readout. If it cannot be read, show "hardware: unverified" rather than a guess.
- Mode text and color change with the active tier: LIVE (AMD vLLM) → REPLAY (cached real outputs, known demo cases) → TEMPLATE (any other case).
- The P(win) label stays "synthetic-trained" until a calibration check (reliability curve or Brier score on held-out synthetic data) is saved in docs/evidence/. Only then may it read "synthetic-calibrated".
- Pitch angle: the degradation ladder is a feature. Show it working in the video (video_script.md, 3:40).
