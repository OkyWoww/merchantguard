// MerchantGuard Single-Screen UI Controller

const API_BASE = window.location.origin;

async function loadHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("llm-mode-badge");
      if (badge) {
        badge.textContent = data.llm_mode === "vllm" ? "AMD ROCm vLLM" : "Replay Cache";
      }
    }
  } catch (e) {
    console.warn("Health check error:", e);
  }
}

async function loadCases() {
  const container = document.getElementById("cases-list");
  if (!container) return;
  container.innerHTML = `<div class="text-xs text-slate-500">Loading cases...</div>`;

  try {
    const res = await fetch(`${API_BASE}/cases`);
    const cases = await res.json();
    container.innerHTML = "";

    cases.forEach((c) => {
      const btn = document.createElement("button");
      btn.className = "w-full text-left p-3 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 hover:border-slate-700 transition flex flex-col gap-1";
      btn.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="text-xs font-mono font-bold text-slate-200">${c.case_id}</span>
          <span class="text-xs font-mono text-rose-400">$${c.order_amount.toFixed(2)}</span>
        </div>
        <div class="text-xs text-slate-400 truncate">${c.claimed_reason} · ${c.order_id}</div>
      `;
      btn.onclick = () => selectAndEvaluateCase(c.case_id);
      container.appendChild(btn);
    });

    if (cases.length > 0) {
      selectAndEvaluateCase(cases[0].case_id);
    }
  } catch (e) {
    container.innerHTML = `<div class="text-xs text-rose-400">Failed to load cases. Ensure API is running.</div>`;
  }
}

function selectAndEvaluateCase(caseId) {
  const actionBadge = document.getElementById("action-badge");
  const evVal = document.getElementById("ev-value");
  const pWinVal = document.getElementById("p-win-value");
  const reasonDesc = document.getElementById("reason-desc");
  const rulesList = document.getElementById("rules-list");
  const narrativeSummary = document.getElementById("narrative-summary");
  const draftReply = document.getElementById("draft-reply");

  if (actionBadge) {
    actionBadge.textContent = "STREAMING...";
    actionBadge.className = "text-2xl font-bold mt-1 font-mono text-amber-400 animate-pulse";
  }
  if (rulesList) rulesList.innerHTML = `<div class="text-xs text-slate-400">Evaluating policy rules on AMD backend...</div>`;

  const evtSource = new EventSource(`${API_BASE}/cases/${caseId}/stream`);

  evtSource.addEventListener("gate_evaluated", (e) => {
    const data = JSON.parse(e.data);
    if (rulesList && data.rules) {
      rulesList.innerHTML = "";
      data.rules.forEach((r) => {
        const item = document.createElement("div");
        item.className = `p-2 rounded border flex items-center justify-between ${
          r.passed
            ? "border-emerald-950 bg-emerald-950/20 text-emerald-300"
            : "border-rose-950 bg-rose-950/20 text-rose-300"
        }`;
        item.innerHTML = `
          <div>
            <span class="font-mono font-bold">${r.rule_id}</span>: ${r.rule_name}
            <div class="text-[11px] opacity-80 mt-0.5">${r.details}</div>
          </div>
          <span class="font-mono text-xs px-2 py-0.5 rounded ${
            r.passed ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
          }">${r.passed ? "PASS" : "TRIGGERED"}</span>
        `;
        rulesList.appendChild(item);
      });
    }
  });

  evtSource.addEventListener("margin_computed", (e) => {
    const data = JSON.parse(e.data);
    if (actionBadge) {
      actionBadge.textContent = data.action;
      actionBadge.className = "text-2xl font-bold mt-1 font-mono " + (
        data.action === "CONTEST" ? "text-emerald-400" :
        data.action === "ACCEPT_REFUND" ? "text-rose-400" :
        data.action === "PARTIAL_REFUND" ? "text-sky-400" : "text-amber-400"
      );
    }
    if (evVal) evVal.textContent = (data.expected_margin_recovery >= 0 ? "+$" : "-$") + Math.abs(data.expected_margin_recovery).toFixed(2);
    if (pWinVal) pWinVal.textContent = `P(Win): ${(data.p_win * 100).toFixed(1)}%`;
    if (reasonDesc) reasonDesc.textContent = `Reason Code: ${data.reason_code} · Gate Status: ${data.gate_status}`;
  });

  evtSource.addEventListener("narrative_generated", (e) => {
    const data = JSON.parse(e.data);
    if (narrativeSummary) narrativeSummary.textContent = data.summary;
    if (draftReply) draftReply.textContent = data.draft_reply;
  });

  evtSource.addEventListener("complete", () => {
    evtSource.close();
  });

  evtSource.onerror = () => {
    evtSource.close();
  };
}

document.addEventListener("DOMContentLoaded", () => {
  loadHealth();
  loadCases();

  const verifyBtn = document.getElementById("btn-verify-audit");
  if (verifyBtn) {
    verifyBtn.onclick = async () => {
      try {
        const res = await fetch(`${API_BASE}/audit/verify`);
        const data = await res.json();
        alert(`Audit Chain Status: ${data.valid ? "VALID" : "CORRUPTED"}\nTotal Blocks: ${data.total_blocks}\n${data.message}`);
      } catch (e) {
        alert("Failed to verify audit chain: " + e.message);
      }
    };
  }
});
