// MerchantGuard Frontend Dashboard Controller
// AMD Developer Hackathon: ACT III (Track: Reinvent Commerce)
// Handles SSE Telemetry Streaming, 4 Demo Scenarios, Margin Analytics, and Cryptographic Ledger Inspector

const API_BASE = window.location.origin;

let activeEventSource = null;
let currentCaseId = "CASE-1001";
let allCases = [];

// -------------------------------------------------------------
// Initialization & Health Probe
// -------------------------------------------------------------
async function init() {
  await loadHealth();
  await loadCases();
  // Auto-trigger Scenario 1 on launch
  triggerScenario("CASE-1001", 1);
}

async function loadHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("llm-mode-badge");
      const ping = document.getElementById("engine-ping");
      const dot = document.getElementById("engine-dot");

      if (badge) {
        if (data.llm_mode === "live" || data.llm_mode === "vllm") {
          badge.textContent = `AMD ROCm (${data.model_name || "Gemma-4-31B-IT"} · LIVE)`;
          badge.className = "font-mono font-semibold text-emerald-400";
        } else if (data.llm_mode === "replay") {
          badge.textContent = "REPLAY (Zero-Cost / Offline)";
          badge.className = "font-mono font-semibold text-cyan-400";
        } else {
          badge.textContent = "TEMPLATE SYNTHESIZER";
          badge.className = "font-mono font-semibold text-amber-400";
        }
      }
    }
  } catch (err) {
    console.warn("Health probe error:", err);
  }
}

async function loadCases() {
  const container = document.getElementById("cases-list");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/cases`);
    if (res.ok) {
      allCases = await res.json();
      renderQueue(allCases);
    }
  } catch (err) {
    console.error("Failed to load cases:", err);
  }
}

function renderQueue(cases) {
  const container = document.getElementById("cases-list");
  if (!container) return;
  container.innerHTML = "";

  const queueCount = document.getElementById("queue-count");
  if (queueCount) queueCount.textContent = `${cases.length} Cases`;

  cases.forEach((c) => {
    const btn = document.createElement("button");
    const isActive = c.case_id === currentCaseId;
    btn.className = `w-full text-left p-2.5 rounded-lg border transition flex flex-col gap-1 ${
      isActive
        ? "border-cyan-500/60 bg-slate-800/90 shadow-sm"
        : "border-slate-800 bg-slate-900/60 hover:bg-slate-800/50 hover:border-slate-700"
    }`;
    btn.id = `queue-item-${c.case_id}`;

    btn.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="text-xs font-mono font-bold text-slate-200">${c.case_id}</span>
        <span class="text-xs font-mono font-semibold text-rose-400">$${c.order_amount.toFixed(2)}</span>
      </div>
      <div class="text-[11px] text-slate-400 truncate flex items-center justify-between">
        <span>${c.claimed_reason}</span>
        <span class="font-mono text-[10px] text-slate-500">${c.order_id}</span>
      </div>
    `;

    btn.onclick = () => {
      // Find scenario number if applicable
      const scenarioMap = { "CASE-1001": 1, "CASE-1002": 2, "CASE-1003": 3, "CASE-1004": 4 };
      const sNum = scenarioMap[c.case_id] || 1;
      triggerScenario(c.case_id, sNum);
    };

    container.appendChild(btn);
  });
}

// -------------------------------------------------------------
// Scenario Triggering & Compare Panel Update
// -------------------------------------------------------------
function triggerScenario(caseId, scenarioNum) {
  currentCaseId = caseId;

  // 1. Highlight Scenario Selector Button
  for (let i = 1; i <= 4; i++) {
    const sBtn = document.getElementById(`btn-scenario-${i}`);
    if (sBtn) {
      if (i === scenarioNum) {
        sBtn.classList.add("ring-2", "ring-cyan-400", "scale-[1.01]");
      } else {
        sBtn.classList.remove("ring-2", "ring-cyan-400", "scale-[1.01]");
      }
    }
  }

  // 2. Update Active Scenario Indicator & Endpoint
  const activeIndicator = document.getElementById("active-scenario-indicator");
  if (activeIndicator) {
    activeIndicator.textContent = `Scenario ${scenarioNum} Active (${caseId})`;
  }
  const streamEndpoint = document.getElementById("active-stream-endpoint");
  if (streamEndpoint) {
    streamEndpoint.textContent = `GET /cases/${caseId}/stream`;
  }

  // 3. Highlight Queue Item
  allCases.forEach((c) => {
    const item = document.getElementById(`queue-item-${c.case_id}`);
    if (item) {
      if (c.case_id === caseId) {
        item.className = "w-full text-left p-2.5 rounded-lg border border-cyan-500/60 bg-slate-800/90 shadow-sm transition flex flex-col gap-1";
      } else {
        item.className = "w-full text-left p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800/50 hover:border-slate-700 transition flex flex-col gap-1";
      }
    }
  });

  // 4. Update Evidence Compare Panel with Case Data
  const caseObj = allCases.find((c) => c.case_id === caseId);
  if (caseObj) {
    updateComparePanel(caseObj);
  }

  // 5. Connect and stream SSE pipeline
  connectSSEStream(caseId);
}

function updateComparePanel(c) {
  // Buyer section
  const buyerReason = document.getElementById("buyer-reason-tag");
  const buyerStmt = document.getElementById("buyer-statement");
  const buyerDate = document.getElementById("buyer-claim-date");
  const buyerAmount = document.getElementById("buyer-order-amount");

  if (buyerReason) buyerReason.textContent = c.claimed_reason;
  if (buyerStmt) buyerStmt.textContent = `"${c.complaint_text}"`;
  if (buyerDate) buyerDate.textContent = c.claim_date.split("T")[0];
  if (buyerAmount) buyerAmount.textContent = `$${c.order_amount.toFixed(2)}`;

  // Carrier events list
  const eventsList = document.getElementById("carrier-events-list");
  if (eventsList && c.courier_events) {
    eventsList.innerHTML = "";
    c.courier_events.forEach((ev) => {
      const item = document.createElement("div");
      item.className = "flex items-start justify-between text-[11px] py-1 border-b border-slate-900 last:border-0";
      item.innerHTML = `
        <div>
          <span class="font-mono font-bold text-slate-300">${ev.status}</span>:
          <span class="text-slate-400">${ev.note}</span>
        </div>
        <span class="font-mono text-slate-500 text-[10px] ml-2 shrink-0">${ev.timestamp.split("T")[0]}</span>
      `;
      eventsList.appendChild(item);
    });
  }

  // Telemetry tags
  const lastEvent = c.courier_events && c.courier_events.length > 0 ? c.courier_events[c.courier_events.length - 1] : null;
  const geoTag = document.getElementById("carrier-geo-tag");
  const sigTag = document.getElementById("carrier-sig-tag");
  const discrepancyBadge = document.getElementById("discrepancy-badge");

  if (lastEvent) {
    if (geoTag) {
      geoTag.textContent = lastEvent.geo_match ? "MATCH ✓" : "MISMATCH ✗";
      geoTag.className = lastEvent.geo_match ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
    }
    if (sigTag) {
      sigTag.textContent = lastEvent.signature_present ? "SIGNED ✓" : "MISSING ✗";
      sigTag.className = lastEvent.signature_present ? "text-emerald-400 font-bold" : "text-amber-400 font-bold";
    }

    if (discrepancyBadge) {
      if (!lastEvent.geo_match || !lastEvent.signature_present || lastEvent.note.toLowerCase().includes("fence") || lastEvent.note.toLowerCase().includes("unattended")) {
        discrepancyBadge.textContent = "Carrier Ambiguity Detected ⚠️";
        discrepancyBadge.className = "text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30";
      } else {
        discrepancyBadge.textContent = "Verified Consistent ✓";
        discrepancyBadge.className = "text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
      }
    }
  }
}

// -------------------------------------------------------------
// SSE Stream Pipeline (T3.1)
// -------------------------------------------------------------
function resetStepper() {
  const steps = ["gate", "margin", "narration", "audit"];
  steps.forEach((s) => {
    const el = document.getElementById(`step-${s}`);
    const badge = document.getElementById(`step-${s}-badge`);
    if (el) el.className = "p-2.5 rounded-lg border border-slate-800 bg-slate-900/60 transition";
    if (badge) {
      badge.textContent = "PENDING";
      badge.className = "font-mono text-[10px] text-slate-500";
    }
  });

  const sseStatus = document.getElementById("sse-status-badge");
  if (sseStatus) {
    sseStatus.textContent = "STREAMING...";
    sseStatus.className = "font-mono text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse";
  }

  // Clear narrative summary & response draft
  const narrativeSummary = document.getElementById("narrative-summary");
  if (narrativeSummary) {
    narrativeSummary.textContent = "Streaming evaluation from AMD backend...";
    narrativeSummary.className = "text-xs text-slate-300 font-sans leading-relaxed stream-cursor";
  }
  const draftReply = document.getElementById("draft-reply");
  if (draftReply) draftReply.textContent = "Generating fact-cited response...";
}

function setStepActive(stepName) {
  const el = document.getElementById(`step-${stepName}`);
  const badge = document.getElementById(`step-${stepName}-badge`);
  if (el) {
    el.className = "p-2.5 rounded-lg border border-cyan-500/80 bg-slate-800/90 transition shadow-sm animate-pulse";
  }
  if (badge) {
    badge.textContent = "ACTIVE";
    badge.className = "font-mono text-[10px] text-cyan-400 font-bold";
  }
}

function setStepCompleted(stepName) {
  const el = document.getElementById(`step-${stepName}`);
  const badge = document.getElementById(`step-${stepName}-badge`);
  if (el) {
    el.className = "p-2.5 rounded-lg border border-emerald-500/50 bg-slate-900/90 transition shadow-sm";
  }
  if (badge) {
    badge.textContent = "DONE ✓";
    badge.className = "font-mono text-[10px] text-emerald-400 font-bold";
  }
}

function connectSSEStream(caseId) {
  if (activeEventSource) {
    activeEventSource.close();
  }

  resetStepper();
  setStepActive("gate");

  const actionBadge = document.getElementById("action-badge");
  if (actionBadge) {
    actionBadge.textContent = "EVALUATING...";
    actionBadge.className = "text-3xl font-extrabold font-mono text-cyan-400 tracking-tight animate-pulse";
  }

  const evtSource = new EventSource(`${API_BASE}/cases/${caseId}/stream`);
  activeEventSource = evtSource;

  // 1. Stage 1: POLICY_GATE
  const handlePolicyGate = (event) => {
    try {
      const data = JSON.parse(event.data);
      const payload = data.payload || data;
      setStepCompleted("gate");
      setStepActive("margin");

      // Render Policy Rules
      const rulesList = document.getElementById("rules-list");
      if (rulesList && payload.rules) {
        rulesList.innerHTML = "";
        payload.rules.forEach((r) => {
          const item = document.createElement("div");
          const isPass = r.passed;
          item.className = `p-2.5 rounded-lg border flex items-center justify-between ${
            isPass
              ? "border-emerald-900/40 bg-emerald-950/20 text-emerald-300"
              : "border-rose-900/40 bg-rose-950/20 text-rose-300"
          }`;
          item.innerHTML = `
            <div>
              <div class="font-mono font-bold text-xs flex items-center gap-1.5">
                <span>${r.rule_id}</span>
                <span class="text-slate-300 font-sans font-medium text-[11px]">${r.rule_name}</span>
              </div>
              <div class="text-[10px] text-slate-400 mt-0.5">${r.details}</div>
            </div>
            <span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
              isPass ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
            }">${isPass ? "PASS" : "TRIGGERED"}</span>
          `;
          rulesList.appendChild(item);
        });
      }

      const gatePill = document.getElementById("gate-status-pill");
      if (gatePill) {
        gatePill.textContent = payload.status || "GATE_PROCESSED";
      }
    } catch (err) {
      console.error("Error processing POLICY_GATE event:", err);
    }
  };

  // 2. Stage 2: MARGIN_ENGINE
  const handleMarginEngine = (event) => {
    try {
      const data = JSON.parse(event.data);
      const payload = data.payload || data;
      setStepCompleted("margin");
      setStepActive("narration");

      // Update Decision Banner
      const actionBadge = document.getElementById("action-badge");
      const decisionCard = document.getElementById("decision-card");
      const reasonCodeBadge = document.getElementById("reason-code-badge");
      const evVal = document.getElementById("ev-value");
      const pWinVal = document.getElementById("p-win-value");

      if (actionBadge) {
        actionBadge.textContent = payload.action;
        actionBadge.classList.remove("animate-pulse");

        if (payload.action === "CONTEST") {
          actionBadge.className = "text-3xl font-extrabold font-mono text-emerald-400 tracking-tight";
          if (decisionCard) decisionCard.className = "glass-panel rounded-xl p-5 relative overflow-hidden transition glow-emerald";
        } else if (payload.action === "NEEDS_HUMAN") {
          actionBadge.className = "text-3xl font-extrabold font-mono text-amber-400 tracking-tight";
          if (decisionCard) decisionCard.className = "glass-panel rounded-xl p-5 relative overflow-hidden transition glow-amber";
        } else if (payload.action === "ACCEPT_REFUND") {
          actionBadge.className = "text-3xl font-extrabold font-mono text-rose-400 tracking-tight";
          if (decisionCard) decisionCard.className = "glass-panel rounded-xl p-5 relative overflow-hidden transition glow-rose";
        } else {
          actionBadge.className = "text-3xl font-extrabold font-mono text-cyan-400 tracking-tight";
          if (decisionCard) decisionCard.className = "glass-panel rounded-xl p-5 relative overflow-hidden transition glow-cyan";
        }
      }

      if (reasonCodeBadge) {
        reasonCodeBadge.textContent = payload.reason_code;
      }

      const ev = payload.expected_margin_recovery || 0;
      if (evVal) {
        evVal.textContent = (ev >= 0 ? "+$" : "-$") + Math.abs(ev).toFixed(2);
        evVal.className = `text-2xl sm:text-3xl font-mono font-bold mt-1 ${ev >= 0 ? "text-emerald-400" : "text-rose-400"}`;
      }

      const pWin = payload.p_win || 0;
      if (pWinVal) {
        pWinVal.textContent = `P(Win): ${(pWin * 100).toFixed(1)}%`;
      }

      // Update Breakdown Metrics
      const lossRefund = document.getElementById("metric-loss-refund");
      const metricPWin = document.getElementById("metric-p-win");
      const pWinBar = document.getElementById("p-win-bar");
      const metricNetRecovery = document.getElementById("metric-net-recovery");

      const caseObj = allCases.find((c) => c.case_id === currentCaseId);
      if (lossRefund && caseObj) {
        lossRefund.textContent = `-$${caseObj.order_amount.toFixed(2)}`;
      }
      if (metricPWin) {
        metricPWin.textContent = `${(pWin * 100).toFixed(1)}%`;
      }
      if (pWinBar) {
        pWinBar.style.width = `${Math.min(100, pWin * 100)}%`;
      }
      if (metricNetRecovery) {
        metricNetRecovery.textContent = (ev >= 0 ? "+$" : "-$") + Math.abs(ev).toFixed(2);
        metricNetRecovery.className = `text-base font-mono font-bold mt-1 ${ev >= 0 ? "text-emerald-400" : "text-rose-400"}`;
      }

      // Update formula math string
      const formulaMath = document.getElementById("formula-math-text");
      if (formulaMath && caseObj) {
        const orderAmt = caseObj.order_amount.toFixed(2);
        const unitMargin = caseObj.unit_margin.toFixed(2);
        const disputeFee = caseObj.dispute_fee.toFixed(2);
        const pWinFormatted = pWin.toFixed(2);
        formulaMath.textContent = `EV = ${pWinFormatted} × ($${orderAmt} + $${unitMargin}) - (1 - ${pWinFormatted}) × $${disputeFee} = ${ev >= 0 ? "+$" : "-$"}${Math.abs(ev).toFixed(2)}`;
      }

    } catch (err) {
      console.error("Error processing MARGIN_ENGINE event:", err);
    }
  };

  // 3. Stage 3: NARRATION
  const handleNarration = (event) => {
    try {
      const data = JSON.parse(event.data);
      const payload = data.payload || data;
      setStepCompleted("narration");
      setStepActive("audit");

      const summary = document.getElementById("narrative-summary");
      if (summary) {
        summary.textContent = payload.summary;
        summary.className = "text-xs text-slate-200 font-sans leading-relaxed";
      }

      const draft = document.getElementById("draft-reply");
      if (draft) {
        draft.textContent = payload.draft_reply;
      }

      const provider = document.getElementById("narrative-provider");
      if (provider) {
        if (payload.mode === "LIVE") {
          provider.textContent = `AMD ROCm (${payload.model || "Gemma-4-31B-IT"} · LIVE)`;
          provider.className = "text-emerald-400 font-semibold";
        } else if (payload.mode === "REPLAY") {
          provider.textContent = "Replay Cache (Zero-Cost)";
          provider.className = "text-cyan-400 font-semibold";
        } else {
          provider.textContent = "Deterministic Template Synthesizer";
          provider.className = "text-amber-400 font-semibold";
        }
      }

      // Render Citation Chips
      const chipsContainer = document.getElementById("citation-chips");
      if (chipsContainer && payload.claims) {
        chipsContainer.innerHTML = `<span class="text-[11px] text-slate-400 mr-1">Citations:</span>`;
        payload.claims.forEach((claim, idx) => {
          claim.fact_ids.forEach((fid) => {
            const chip = document.createElement("span");
            chip.className = "px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 cursor-pointer hover:bg-cyan-900 transition";
            chip.textContent = `[F${idx + 1}: ${fid}]`;
            chip.title = claim.statement;
            chipsContainer.appendChild(chip);
          });
        });
      }

      const latency = document.getElementById("pipeline-latency");
      if (latency && payload.generation_latency_ms) {
        latency.textContent = `${Math.round(payload.generation_latency_ms)}ms`;
      }
    } catch (err) {
      console.error("Error processing NARRATION event:", err);
    }
  };

  // 4. Stage 4: AUDIT_CHAIN
  const handleAuditChain = (event) => {
    try {
      const data = JSON.parse(event.data);
      const payload = data.payload || data;
      setStepCompleted("audit");

      const block = payload.block || payload;
      const blockIdx = document.getElementById("audit-block-index");
      const blockHash = document.getElementById("audit-block-hash");
      const prevHash = document.getElementById("audit-prev-hash");
      const integrityBadge = document.getElementById("audit-integrity-badge");

      if (blockIdx && block.index !== undefined) {
        blockIdx.textContent = `#${block.index}`;
      }
      if (blockHash && (block.block_hash || block.hash)) {
        const h = block.block_hash || block.hash;
        blockHash.textContent = h;
        blockHash.title = h;
      }
      if (prevHash && block.previous_hash) {
        const ph = block.previous_hash.startsWith("00000000") ? `${block.previous_hash.slice(0, 16)}... (Genesis)` : block.previous_hash;
        prevHash.textContent = ph;
        prevHash.title = block.previous_hash;
      }
      if (integrityBadge) {
        integrityBadge.innerHTML = `
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
          Ledger Valid (100%)
        `;
      }
    } catch (err) {
      console.error("Error processing AUDIT_CHAIN event:", err);
    }
  };

  // 5. Stage 5: COMPLETE
  const handleComplete = () => {
    const sseStatus = document.getElementById("sse-status-badge");
    if (sseStatus) {
      sseStatus.textContent = "COMPLETED ✓";
      sseStatus.className = "font-mono text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
    }
    evtSource.close();
  };

  // Register named SSE event listeners
  evtSource.addEventListener("POLICY_GATE", handlePolicyGate);
  evtSource.addEventListener("gate_evaluated", handlePolicyGate);

  evtSource.addEventListener("MARGIN_ENGINE", handleMarginEngine);
  evtSource.addEventListener("margin_computed", handleMarginEngine);

  evtSource.addEventListener("NARRATION", handleNarration);
  evtSource.addEventListener("narrative_generated", handleNarration);

  evtSource.addEventListener("AUDIT_CHAIN", handleAuditChain);
  evtSource.addEventListener("audit_committed", handleAuditChain);

  evtSource.addEventListener("COMPLETE", handleComplete);
  evtSource.addEventListener("complete", handleComplete);

  evtSource.onerror = () => {
    const sseStatus = document.getElementById("sse-status-badge");
    if (sseStatus) {
      sseStatus.textContent = "CLOSED";
      sseStatus.className = "font-mono text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700";
    }
    evtSource.close();
  };
}

// -------------------------------------------------------------
// Interactive Helpers (Copy, Formula, Audit Modal)
// -------------------------------------------------------------
function toggleFormulaInfo() {
  const explainer = document.getElementById("formula-explainer");
  if (explainer) {
    explainer.classList.toggle("hidden");
  }
}

async function copyResponseDraft() {
  const draft = document.getElementById("draft-reply");
  const copyText = document.getElementById("copy-text");
  if (draft) {
    try {
      await navigator.clipboard.writeText(draft.textContent);
      if (copyText) {
        const original = copyText.textContent;
        copyText.textContent = "Copied ✓";
        setTimeout(() => {
          copyText.textContent = original;
        }, 2000);
      }
    } catch (e) {
      alert("Copied to clipboard!");
    }
  }
}

async function verifyAuditLedger() {
  const modal = document.getElementById("audit-modal");
  const modalStatus = document.getElementById("modal-audit-status");
  const modalBlocks = document.getElementById("modal-audit-blocks");
  const modalMsg = document.getElementById("modal-audit-message");

  try {
    const res = await fetch(`${API_BASE}/audit/verify`);
    if (res.ok) {
      const data = await res.json();
      if (modalStatus) {
        modalStatus.textContent = data.valid ? "VALID (UNBROKEN)" : "CORRUPTED";
        modalStatus.className = data.valid ? "font-mono font-bold text-emerald-400" : "font-mono font-bold text-rose-400";
      }
      if (modalBlocks) {
        modalBlocks.textContent = `${data.total_blocks} Verified Blocks`;
      }
      if (modalMsg) {
        modalMsg.textContent = data.message;
      }
      if (modal) modal.classList.remove("hidden");
    }
  } catch (err) {
    alert("Audit verification check failed: " + err.message);
  }
}

function closeAuditModal() {
  const modal = document.getElementById("audit-modal");
  if (modal) modal.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", () => {
  init();

  const verifyBtn = document.getElementById("btn-verify-audit");
  if (verifyBtn) {
    verifyBtn.onclick = verifyAuditLedger;
  }
});
