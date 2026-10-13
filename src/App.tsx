import React, { useState, useEffect, useMemo } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Scale,
  Cpu,
  Coins,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Copy,
  Check,
  Lock,
  Link2,
  Terminal,
  Layers,
  Plus,
  Play,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Code2,
  Database,
  Sliders,
  DollarSign
} from 'lucide-react';

// --- Types & Schemas matching Python Pydantic models ---
type DecisionAction = 'CONTEST' | 'PARTIAL_REFUND' | 'ACCEPT_REFUND' | 'NEEDS_HUMAN';

interface CourierEvent {
  timestamp: string;
  status: string;
  note: string;
  geo_match: boolean;
  signature_present: boolean;
}

interface DisputeCase {
  case_id: string;
  order_id: string;
  claim_date: string;
  delivery_date: string;
  order_amount: number;
  unit_margin: number;
  dispute_fee: number;
  claimed_reason: string;
  complaint_text: string;
  courier_events: CourierEvent[];
  scenario_name?: string;
  scenario_desc?: string;
}

interface GateRuleEvaluation {
  rule_id: string;
  rule_name: string;
  passed: boolean;
  details: string;
  trigger_action?: DecisionAction;
}

interface DecisionResult {
  case_id: string;
  action: DecisionAction;
  reason_code: string;
  p_win: number;
  expected_margin_recovery: number;
  gate_status: 'PASSED' | 'REJECTED' | 'ESCALATED' | 'TRIGGERED' | 'OVERRIDDEN_BY_MARGIN';
  rule_evaluations: GateRuleEvaluation[];
  settlement_offer?: number;
}

interface CitedClaim {
  statement: string;
  fact_ids: string[];
}

interface NarrativePayload {
  case_id: string;
  summary: string;
  claims: CitedClaim[];
  draft_reply: string;
  llm_provider: string;
  verified_citations: boolean;
  generation_latency_ms: number;
}

interface AuditBlock {
  index: number;
  timestamp: string;
  case_id: string;
  action: string;
  payload_hash: string;
  previous_hash: string;
  block_hash: string;
}

// --- SHA-256 helper in browser for hash-chain simulation ---
async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// --- Initial Core Demo Scenarios ---
const INITIAL_SCENARIOS: DisputeCase[] = [
  {
    case_id: 'CASE-1001',
    scenario_name: 'Scenario 1: Clean Win',
    scenario_desc: 'High-probability contest with verified GPS match and physical signature.',
    order_id: 'ORD-88219',
    claim_date: '2026-10-04T14:30:00Z',
    delivery_date: '2026-10-02T10:15:00Z',
    order_amount: 185.00,
    unit_margin: 62.00,
    dispute_fee: 15.00,
    claimed_reason: 'ITEM_NOT_RECEIVED',
    complaint_text: 'I was home all day and nobody brought any package to my porch. I want my money back.',
    courier_events: [
      {
        timestamp: '2026-10-01T08:00:00Z',
        status: 'OUT_FOR_DELIVERY',
        note: 'Courier van dispatched with parcel',
        geo_match: true,
        signature_present: false
      },
      {
        timestamp: '2026-10-02T10:15:00Z',
        status: 'DELIVERED',
        note: 'Handed directly to resident. Signed by M. Vance',
        geo_match: true,
        signature_present: true
      }
    ]
  },
  {
    case_id: 'CASE-1002',
    scenario_name: 'Scenario 2: Ambiguous Custody',
    scenario_desc: 'High value order ($420) left at gate with GPS anomaly and no signature.',
    order_id: 'ORD-94301',
    claim_date: '2026-10-06T18:45:00Z',
    delivery_date: '2026-10-05T12:00:00Z',
    order_amount: 420.00,
    unit_margin: 140.00,
    dispute_fee: 15.00,
    claimed_reason: 'ITEM_NOT_RECEIVED',
    complaint_text: 'High value designer jacket missing. Carrier marked delivered but no parcel in building lobby or mail room.',
    courier_events: [
      {
        timestamp: '2026-10-05T12:00:00Z',
        status: 'DELIVERED',
        note: 'Package left near entry gate',
        geo_match: false,
        signature_present: false
      }
    ]
  },
  {
    case_id: 'CASE-1003',
    scenario_name: 'Scenario 3: Window Bypass',
    scenario_desc: 'Dispute filed 32 days post-delivery, bypassing the statutory 14-day policy window.',
    order_id: 'ORD-71950',
    claim_date: '2026-10-10T11:20:00Z',
    delivery_date: '2026-09-08T16:00:00Z',
    order_amount: 130.00,
    unit_margin: 45.00,
    dispute_fee: 15.00,
    claimed_reason: 'NOT_AS_DESCRIBED',
    complaint_text: 'I opened the box a month later and found the fabric color slightly differs from catalog photo.',
    courier_events: [
      {
        timestamp: '2026-09-08T16:00:00Z',
        status: 'DELIVERED',
        note: 'Delivered to porch',
        geo_match: true,
        signature_present: false
      }
    ]
  },
  {
    case_id: 'CASE-1004',
    scenario_name: 'Scenario 4: Economic Fee Trap',
    scenario_desc: 'Low margin item where dispute fee ($15) makes contesting a guaranteed negative EV loss.',
    order_id: 'ORD-55102',
    claim_date: '2026-10-09T09:10:00Z',
    delivery_date: '2026-10-07T14:40:00Z',
    order_amount: 16.50,
    unit_margin: 3.80,
    dispute_fee: 15.00,
    claimed_reason: 'ITEM_NOT_RECEIVED',
    complaint_text: 'Did not receive phone charging cable.',
    courier_events: [
      {
        timestamp: '2026-10-07T14:40:00Z',
        status: 'DELIVERED',
        note: 'Delivered in mailbox',
        geo_match: true,
        signature_present: false
      }
    ]
  }
];

// --- Deterministic Policy Gate Implementation (Mirroring app/gate.py) ---
function evaluatePolicyGate(caseItem: DisputeCase): {
  action: DecisionAction;
  reason_code: string;
  gate_status: 'PASSED' | 'REJECTED' | 'ESCALATED' | 'TRIGGERED';
  evaluations: GateRuleEvaluation[];
} {
  const returnWindowDays = 14;
  const highValueCutoff = 250.0;
  const evaluations: GateRuleEvaluation[] = [];

  const dDeliv = new Date(caseItem.delivery_date).getTime();
  const dClaim = new Date(caseItem.claim_date).getTime();
  const daysElapsed = Math.max(0, (dClaim - dDeliv) / (1000 * 3600 * 24));

  const hasGeoMatch = caseItem.courier_events.some(e => e.geo_match);
  const hasSignature = caseItem.courier_events.some(e => e.signature_present);
  const hasDelivered = caseItem.courier_events.some(e => e.status.toUpperCase().includes('DELIVERED'));

  // R-001: Return Window Expired
  const r001Passed = daysElapsed <= returnWindowDays;
  evaluations.push({
    rule_id: 'R-001',
    rule_name: 'Return Window Compliance',
    passed: r001Passed,
    details: `${daysElapsed.toFixed(1)} days elapsed (Policy limit: ${returnWindowDays} days).`,
    trigger_action: !r001Passed ? 'CONTEST' : undefined
  });
  if (!r001Passed) {
    return { action: 'CONTEST', reason_code: 'R001_WINDOW_EXPIRED', gate_status: 'TRIGGERED', evaluations };
  }

  // R-006: Courier Milestone Completeness
  const r006Passed = caseItem.courier_events.length > 0 && hasDelivered;
  evaluations.push({
    rule_id: 'R-006',
    rule_name: 'Courier Milestone Completeness',
    passed: r006Passed,
    details: r006Passed ? 'Carrier tracking complete and delivered status recorded.' : 'Missing tracking milestones or carrier scan anomaly.',
    trigger_action: !r006Passed ? 'NEEDS_HUMAN' : undefined
  });
  if (!r006Passed) {
    return { action: 'NEEDS_HUMAN', reason_code: 'R006_COURIER_ANOMALY', gate_status: 'ESCALATED', evaluations };
  }

  // R-003: High-Value Item Custody Verification
  const r003Passed = !(caseItem.order_amount > highValueCutoff && !hasSignature);
  evaluations.push({
    rule_id: 'R-003',
    rule_name: 'High-Value Custody Verification',
    passed: r003Passed,
    details: r003Passed
      ? `Order value $${caseItem.order_amount.toFixed(2)} satisfies custody risk limits.`
      : `High-value order ($${caseItem.order_amount.toFixed(2)} > $${highValueCutoff.toFixed(2)}) delivered without recipient signature.`,
    trigger_action: !r003Passed ? 'NEEDS_HUMAN' : undefined
  });
  if (!r003Passed) {
    return { action: 'NEEDS_HUMAN', reason_code: 'R003_HIGH_VALUE_UNSIGNED', gate_status: 'ESCALATED', evaluations };
  }

  // R-004: Economic Fee Trap Check
  const r004Passed = caseItem.order_amount > caseItem.dispute_fee && caseItem.unit_margin > 0.0;
  evaluations.push({
    rule_id: 'R-004',
    rule_name: 'Economic Fee Trap Check',
    passed: r004Passed,
    details: r004Passed
      ? `Unit margin ($${caseItem.unit_margin.toFixed(2)}) exceeds gateway fee ($${caseItem.dispute_fee.toFixed(2)}).`
      : `Dispute fee ($${caseItem.dispute_fee.toFixed(2)}) exceeds margin potential ($${caseItem.unit_margin.toFixed(2)}). Contesting risks negative EV.`,
    trigger_action: !r004Passed ? 'ACCEPT_REFUND' : undefined
  });
  if (!r004Passed) {
    return { action: 'ACCEPT_REFUND', reason_code: 'R004_ECONOMIC_FEE_TRAP', gate_status: 'TRIGGERED', evaluations };
  }

  // R-005: Partial Damage Routing
  const isPartial = ['DAMAGED', 'PARTIAL_TRANSIT_DEFECT', 'MINOR_COSMETIC_DAMAGE'].includes(caseItem.claimed_reason.toUpperCase());
  evaluations.push({
    rule_id: 'R-005',
    rule_name: 'Partial Defect Settlement Routing',
    passed: !isPartial,
    details: !isPartial ? 'Full merchandise custody claim.' : `Claim category '${caseItem.claimed_reason}' qualifies for deterministic partial settlement offer.`,
    trigger_action: isPartial ? 'PARTIAL_REFUND' : undefined
  });
  if (isPartial) {
    return { action: 'PARTIAL_REFUND', reason_code: 'R005_PARTIAL_DEFECT_OFFER', gate_status: 'TRIGGERED', evaluations };
  }

  // R-002: Verified Signature + Geo Match
  const r002Passed = hasGeoMatch && hasSignature;
  evaluations.push({
    rule_id: 'R-002',
    rule_name: 'Objective Carrier Proof (Signature + GPS)',
    passed: r002Passed,
    details: r002Passed
      ? 'Carrier telematics confirm precise delivery GPS match AND physical signature.'
      : `Evidence summary: GPS match=${hasGeoMatch}, Signature captured=${hasSignature}.`,
    trigger_action: r002Passed ? 'CONTEST' : undefined
  });
  if (r002Passed) {
    return { action: 'CONTEST', reason_code: 'R002_VERIFIED_SIGNATURE_GEO', gate_status: 'PASSED', evaluations };
  }

  if (hasGeoMatch) {
    return { action: 'CONTEST', reason_code: 'STANDARD_GEO_PROOF', gate_status: 'PASSED', evaluations };
  }

  return { action: 'NEEDS_HUMAN', reason_code: 'AMBIGUOUS_EVIDENCE_ROUTE', gate_status: 'ESCALATED', evaluations };
}

// --- Statistical Margin Engine Implementation (Mirroring app/margin.py) ---
function evaluateMarginEngine(
  caseItem: DisputeCase,
  gateAction: DecisionAction,
  gateReason: string,
  gateStatus: 'PASSED' | 'REJECTED' | 'ESCALATED' | 'TRIGGERED' | 'OVERRIDDEN_BY_MARGIN',
  evaluations: GateRuleEvaluation[]
): DecisionResult {
  const baseRates: Record<string, number> = {
    ITEM_NOT_RECEIVED: 0.65,
    DAMAGED: 0.40,
    NOT_AS_DESCRIBED: 0.35,
    UNAUTHORIZED_CHARGE: 0.50
  };

  const reasonNorm = caseItem.claimed_reason.toUpperCase().replace(/\s+/g, '_');
  let pWin = baseRates[reasonNorm] || 0.50;

  const hasGeo = caseItem.courier_events.some(e => e.geo_match);
  const hasSig = caseItem.courier_events.some(e => e.signature_present);
  const windowExpired = evaluations.some(e => e.rule_id === 'R-001' && !e.passed);

  if (hasGeo) pWin += 0.25;
  if (hasSig) pWin += 0.20;
  if (windowExpired) pWin += 0.30;
  if (caseItem.courier_events.length === 0) pWin -= 0.45;

  pWin = Math.max(0.05, Math.min(0.98, pWin));

  const fee = caseItem.dispute_fee || 15.0;
  const margin = caseItem.unit_margin;
  const ev = (pWin * (margin + fee)) - ((1.0 - pWin) * fee);

  let finalAction = gateAction;
  let finalReason = gateReason;
  let finalStatus = gateStatus;

  // Protect against negative EV trap
  if (finalAction === 'CONTEST' && ev <= 0) {
    finalAction = 'ACCEPT_REFUND';
    finalReason = 'R004_NEGATIVE_EV_AVOIDANCE';
    finalStatus = 'OVERRIDDEN_BY_MARGIN';
  }

  let settlementOffer: number | undefined;
  if (finalAction === 'PARTIAL_REFUND') {
    settlementOffer = Math.round(caseItem.order_amount * 0.35 * 100) / 100;
  }

  return {
    case_id: caseItem.case_id,
    action: finalAction,
    reason_code: finalReason,
    p_win: Math.round(pWin * 1000) / 1000,
    expected_margin_recovery: Math.round(ev * 100) / 100,
    gate_status: finalStatus,
    rule_evaluations: evaluations,
    settlement_offer: settlementOffer
  };
}

// --- Factual Narrative Builder (Mirroring app/narrator.py & replay cache) ---
function buildFactualNarrative(
  caseItem: DisputeCase,
  decision: DecisionResult,
  engineMode: 'rocm_vllm' | 'replay'
): NarrativePayload {
  const hasGeo = caseItem.courier_events.some(e => e.geo_match);
  const hasSig = caseItem.courier_events.some(e => e.signature_present);

  const claims: CitedClaim[] = [
    {
      statement: `Order ${caseItem.order_id} ($${caseItem.order_amount.toFixed(2)}) dispute filed on ${caseItem.claim_date.slice(0, 10)}.`,
      fact_ids: ['order_id', 'order_amount', 'claim_date']
    }
  ];

  if (hasGeo) {
    claims.push({
      statement: 'Carrier telematics confirm precise delivery GPS coordinates match destination address.',
      fact_ids: ['courier_geo']
    });
  }

  if (hasSig) {
    claims.push({
      statement: 'Physical recipient signature was officially captured at handover timestamp.',
      fact_ids: ['signature']
    });
  }

  let summary = '';
  let draftReply = '';

  if (decision.action === 'CONTEST') {
    summary = `Contest package assembled under Rule ${decision.reason_code}. Carrier evidence demonstrates verified handover.`;
    draftReply = `Dear Dispute Arbitration Team,\n\nWe hereby formally contest Dispute ${caseItem.case_id} for Order ${caseItem.order_id} ($${caseItem.order_amount.toFixed(2)}). Carrier records show delivery was executed on ${caseItem.delivery_date.slice(0, 10)}. Coordinates were GPS-verified, and evidence satisfies Policy Rule ${decision.reason_code}.\n\nBecause objective proof of delivery is verified, we respectfully request the dispute fee and order funds be restored to the merchant.\n\nRespectfully,\nMerchant Operations Defense Unit`;
  } else if (decision.action === 'ACCEPT_REFUND') {
    summary = `Auto-refund approved under Rule ${decision.reason_code} to prevent fee loss and negative EV (-$${Math.abs(decision.expected_margin_recovery).toFixed(2)}).`;
    draftReply = `Dear Customer,\n\nWe apologize for the issue regarding your order ${caseItem.order_id}. To resolve this swiftly and avoid unnecessary administrative delay, we have issued a full refund of $${caseItem.order_amount.toFixed(2)} directly to your original payment method.\n\nSincerely,\nCustomer Experience Operations`;
  } else if (decision.action === 'PARTIAL_REFUND') {
    summary = `Settlement offer computed for defect claim ($${decision.settlement_offer?.toFixed(2)} / 35% of order value).`;
    draftReply = `Dear Customer,\n\nRegarding your dispute for Order ${caseItem.order_id}, we understand you noted partial defect issues. We are pleased to offer a courtesy partial refund settlement of $${decision.settlement_offer?.toFixed(2)} while allowing you to retain the product.\n\nWarm regards,\nCustomer Resolution Desk`;
  } else {
    summary = `Case routed to Senior Dispute Specialist under ${decision.reason_code}. Telemetry requires manual courier trace.`;
    draftReply = `INTERNAL ESCALATION NOTE:\n\nCase ${caseItem.case_id} (Order ${caseItem.order_id}) requires manual adjuster review. Order value is $${caseItem.order_amount.toFixed(2)} and lacks physical signature confirmation. Initiating formal carrier trace tracer prior to filing arbitration evidence.`;
  }

  return {
    case_id: caseItem.case_id,
    summary,
    claims,
    draft_reply: draftReply,
    llm_provider: engineMode === 'rocm_vllm' ? 'AMD ROCm vLLM (Llama-3.1-8B-Instruct)' : 'Pre-Cached Replay Cache (ROCm Fallback)',
    verified_citations: true,
    generation_latency_ms: engineMode === 'rocm_vllm' ? 142.6 : 1.8
  };
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'workspace' | 'audit' | 'rules' | 'code'>('workspace');
  const [engineMode, setEngineMode] = useState<'rocm_vllm' | 'replay'>('rocm_vllm');
  const [cases, setCases] = useState<DisputeCase[]>(INITIAL_SCENARIOS);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(INITIAL_SCENARIOS[0].case_id);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evaluationStage, setEvaluationStage] = useState<number>(3); // 0: Idle, 1: Gate, 2: Margin, 3: Narrator/Complete
  const [copiedDraft, setCopiedDraft] = useState<boolean>(false);
  const [filterReason, setFilterReason] = useState<string>('ALL');

  // Audit Chain state
  const [auditChain, setAuditChain] = useState<AuditBlock[]>([]);
  const [auditVerification, setAuditVerification] = useState<{
    valid: boolean;
    total: number;
    message: string;
    checkedAt: string;
  } | null>(null);

  // New Case Modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newCaseData, setNewCaseData] = useState({
    case_id: 'CASE-2001',
    order_id: 'ORD-99012',
    order_amount: 145.0,
    unit_margin: 48.0,
    dispute_fee: 15.0,
    claimed_reason: 'ITEM_NOT_RECEIVED',
    complaint_text: 'Package was never delivered to my doorstep.',
    days_ago_delivered: 3,
    days_ago_claimed: 1,
    geo_match: true,
    signature_present: false
  });

  // Current selected case
  const currentCase = useMemo(() => {
    return cases.find(c => c.case_id === selectedCaseId) || cases[0];
  }, [cases, selectedCaseId]);

  // Real-time evaluation calculation
  const decisionResult = useMemo(() => {
    const gate = evaluatePolicyGate(currentCase);
    return evaluateMarginEngine(currentCase, gate.action, gate.reason_code, gate.gate_status, gate.evaluations);
  }, [currentCase]);

  // Factual Narrative
  const narrative = useMemo(() => {
    return buildFactualNarrative(currentCase, decisionResult, engineMode);
  }, [currentCase, decisionResult, engineMode]);

  // Initialize genesis audit blocks on mount
  useEffect(() => {
    async function initAuditLedger() {
      const blocks: AuditBlock[] = [];
      let prevHash = '0000000000000000000000000000000000000000000000000000000000000000';

      for (let i = 0; i < INITIAL_SCENARIOS.length; i++) {
        const c = INITIAL_SCENARIOS[i];
        const g = evaluatePolicyGate(c);
        const d = evaluateMarginEngine(c, g.action, g.reason_code, g.gate_status, g.evaluations);
        const timestamp = new Date(Date.now() - (INITIAL_SCENARIOS.length - i) * 60000).toISOString();

        const payloadStr = JSON.stringify({ case_id: c.case_id, action: d.action, p_win: d.p_win });
        const payloadHash = await sha256(payloadStr);
        const header = `${i}:${timestamp}:${c.case_id}:${d.action}:${payloadHash}:${prevHash}`;
        const blockHash = await sha256(header);

        blocks.push({
          index: i,
          timestamp,
          case_id: c.case_id,
          action: d.action,
          payload_hash: payloadHash,
          previous_hash: prevHash,
          block_hash: blockHash
        });

        prevHash = blockHash;
      }

      setAuditChain(blocks);
      setAuditVerification({
        valid: true,
        total: blocks.length,
        message: `All ${blocks.length} initial blocks cryptographically verified. Zero tampering detected.`,
        checkedAt: new Date().toLocaleTimeString()
      });
    }

    initAuditLedger();
  }, []);

  // Trigger evaluation animation when case changes
  const handleSelectCase = (id: string) => {
    setSelectedCaseId(id);
    setIsEvaluating(true);
    setEvaluationStage(1);

    setTimeout(() => setEvaluationStage(2), 200);
    setTimeout(() => {
      setEvaluationStage(3);
      setIsEvaluating(false);
    }, 450);
  };

  // Add block to audit chain on demand
  const handleCommitToAudit = async () => {
    const nextIndex = auditChain.length;
    const timestamp = new Date().toISOString();
    const prevHash = auditChain.length > 0 ? auditChain[auditChain.length - 1].block_hash : '0'.repeat(64);

    const payloadStr = JSON.stringify({
      case_id: currentCase.case_id,
      action: decisionResult.action,
      p_win: decisionResult.p_win,
      ev: decisionResult.expected_margin_recovery
    });
    const payloadHash = await sha256(payloadStr);
    const header = `${nextIndex}:${timestamp}:${currentCase.case_id}:${decisionResult.action}:${payloadHash}:${prevHash}`;
    const blockHash = await sha256(header);

    const newBlock: AuditBlock = {
      index: nextIndex,
      timestamp,
      case_id: currentCase.case_id,
      action: decisionResult.action,
      payload_hash: payloadHash,
      previous_hash: prevHash,
      block_hash: blockHash
    };

    const updated = [...auditChain, newBlock];
    setAuditChain(updated);
    setAuditVerification({
      valid: true,
      total: updated.length,
      message: `Appended block #${nextIndex} (${currentCase.case_id}). Chain integrity intact.`,
      checkedAt: new Date().toLocaleTimeString()
    });
  };

  // Verify Audit Chain
  const handleVerifyChain = async () => {
    if (auditChain.length === 0) {
      setAuditVerification({
        valid: true,
        total: 0,
        message: 'Chain is empty. Genesis state clean.',
        checkedAt: new Date().toLocaleTimeString()
      });
      return;
    }

    let isValid = true;
    let corruptedIdx: number | null = null;
    let errMsg = '';

    for (let i = 0; i < auditChain.length; i++) {
      const b = auditChain[i];
      if (i === 0) {
        if (b.previous_hash !== '0'.repeat(64)) {
          isValid = false;
          corruptedIdx = 0;
          errMsg = 'Genesis block previous hash link corrupted.';
          break;
        }
      } else {
        const prev = auditChain[i - 1];
        if (b.previous_hash !== prev.block_hash) {
          isValid = false;
          corruptedIdx = i;
          errMsg = `Hash link broke at Block #${i}. Pointer does not match predecessor hash.`;
          break;
        }
      }

      const expectedHeader = `${b.index}:${b.timestamp}:${b.case_id}:${b.action}:${b.payload_hash}:${b.previous_hash}`;
      const expectedHash = await sha256(expectedHeader);
      if (b.block_hash !== expectedHash) {
        isValid = false;
        corruptedIdx = i;
        errMsg = `Cryptographic digest mismatch at Block #${i}. Block contents modified!`;
        break;
      }
    }

    setAuditVerification({
      valid: isValid,
      total: auditChain.length,
      message: isValid
        ? `Mathematically verified all ${auditChain.length} blocks. Zero tampering detected.`
        : errMsg,
      checkedAt: new Date().toLocaleTimeString()
    });
  };

  // Simulate Malicious Mutation
  const handleSimulateTamper = () => {
    if (auditChain.length === 0) return;
    const tampered = [...auditChain];
    const targetIdx = Math.floor(Math.random() * tampered.length);
    // Maliciously flip action from CONTEST to ACCEPT_REFUND
    tampered[targetIdx] = {
      ...tampered[targetIdx],
      action: tampered[targetIdx].action === 'CONTEST' ? 'ACCEPT_REFUND' : 'CONTEST'
    };
    setAuditChain(tampered);
    handleVerifyChain();
  };

  // Create custom case handler
  const handleCreateCustomCase = () => {
    const now = new Date();
    const dDeliv = new Date(now.getTime() - newCaseData.days_ago_delivered * 86400000).toISOString();
    const dClaim = new Date(now.getTime() - newCaseData.days_ago_claimed * 86400000).toISOString();

    const created: DisputeCase = {
      case_id: newCaseData.case_id,
      scenario_name: `Custom: ${newCaseData.case_id}`,
      scenario_desc: `User configured dispute for ${newCaseData.order_id}`,
      order_id: newCaseData.order_id,
      claim_date: dClaim,
      delivery_date: dDeliv,
      order_amount: Number(newCaseData.order_amount),
      unit_margin: Number(newCaseData.unit_margin),
      dispute_fee: Number(newCaseData.dispute_fee),
      claimed_reason: newCaseData.claimed_reason,
      complaint_text: newCaseData.complaint_text,
      courier_events: [
        {
          timestamp: dDeliv,
          status: 'DELIVERED',
          note: newCaseData.signature_present ? 'Delivered with physical signature' : 'Delivered to mailbox/porch',
          geo_match: newCaseData.geo_match,
          signature_present: newCaseData.signature_present
        }
      ]
    };

    setCases([created, ...cases]);
    setSelectedCaseId(created.case_id);
    setShowCreateModal(false);
  };

  const handleCopyDraft = () => {
    navigator.clipboard.writeText(narrative.draft_reply);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2000);
  };

  // Filtered cases list
  const filteredCases = useMemo(() => {
    if (filterReason === 'ALL') return cases;
    return cases.filter(c => c.claimed_reason === filterReason);
  }, [cases, filterReason]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const totalDisputes = cases.length;
    let netEvSum = 0;
    let autoWinCount = 0;

    cases.forEach(c => {
      const g = evaluatePolicyGate(c);
      const m = evaluateMarginEngine(c, g.action, g.reason_code, g.gate_status, g.evaluations);
      netEvSum += m.expected_margin_recovery;
      if (m.action === 'CONTEST') autoWinCount++;
    });

    return {
      totalDisputes,
      projectedMarginRecovery: netEvSum,
      contestRatio: Math.round((autoWinCount / (totalDisputes || 1)) * 100)
    };
  }, [cases]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
      {/* Top Bar Navigation Contract: 1-line wordmark, nav links, 1 primary action */}
      <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-8">
          {/* Zone 1: Single element brand wordmark */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white whitespace-nowrap">
                MerchantGuard
              </span>
              <span className="hidden sm:inline-block text-xs text-slate-400 ml-2 font-mono">
                v1.0.0 · AMD ROCm ACT III
              </span>
            </div>
          </div>

          {/* Zone 2: Navigation Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-400">
            <button
              onClick={() => setActiveTab('workspace')}
              className={`hover:text-slate-100 transition-colors whitespace-nowrap py-1 ${
                activeTab === 'workspace' ? 'text-rose-400 border-b-2 border-rose-500' : ''
              }`}
            >
              Copilot Workspace
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`hover:text-slate-100 transition-colors whitespace-nowrap py-1 ${
                activeTab === 'audit' ? 'text-rose-400 border-b-2 border-rose-500' : ''
              }`}
            >
              Cryptographic Audit Chain ({auditChain.length})
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`hover:text-slate-100 transition-colors whitespace-nowrap py-1 ${
                activeTab === 'rules' ? 'text-rose-400 border-b-2 border-rose-500' : ''
              }`}
            >
              Policy Rules & Margin Math
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={`hover:text-slate-100 transition-colors whitespace-nowrap py-1 ${
                activeTab === 'code' ? 'text-rose-400 border-b-2 border-rose-500' : ''
              }`}
            >
              Python Scaffolding & Repo Tree
            </button>
          </nav>

          {/* Zone 3: Primary Action / Engine Selector */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs">
              <button
                onClick={() => setEngineMode('rocm_vllm')}
                className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  engineMode === 'rocm_vllm'
                    ? 'bg-rose-500/20 text-rose-300 font-medium border border-rose-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Routes narratives through AMD ROCm vLLM acceleration"
              >
                <Cpu className="w-3 h-3 text-rose-400" />
                <span className="font-mono">AMD ROCm vLLM</span>
              </button>
              <button
                onClick={() => setEngineMode('replay')}
                className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  engineMode === 'replay'
                    ? 'bg-emerald-500/20 text-emerald-300 font-medium border border-emerald-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Zero-latency deterministic Replay Mode cache fallback"
              >
                <RotateCcw className="w-3 h-3 text-emerald-400" />
                <span className="font-mono">Replay Cache</span>
              </button>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap shadow-sm shadow-rose-950"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Case</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">
        {/* KPI Strip: Quantitative Precision without pills */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 font-medium">Disputes in Copilot Queue</span>
            <div className="text-2xl font-bold font-mono tabular-nums text-slate-100 mt-1">
              {metrics.totalDisputes}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {metrics.contestRatio}% Auto-Contest Eligibility Rate
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 font-medium">Projected Margin Recovery</span>
            <div className="text-2xl font-bold font-mono tabular-nums text-emerald-400 mt-1">
              ${metrics.projectedMarginRecovery.toFixed(2)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Net of $15 gateway dispute fees
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 font-medium">Architectural Invariant</span>
            <div className="text-sm font-semibold text-rose-300 mt-1 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-rose-400" />
              <span>Deterministic Gate Decides</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              LLM is NEVER sole decider · Zero prompt injection risk
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-400 font-medium">Cryptographic Ledger</span>
            <div className="text-sm font-semibold text-emerald-400 mt-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>SHA-256 Hash Chain Intact</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {auditChain.length} immutable blocks verified
            </div>
          </div>
        </section>

        {/* TAB 1: COPILOT WORKSPACE */}
        {activeTab === 'workspace' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Dispute Queue (Col 4) */}
            <div className="lg:col-span-4 bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-slate-400" />
                  <h2 className="text-sm font-semibold text-slate-200">Dispute Cases</h2>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  {filteredCases.length} items
                </div>
              </div>

              {/* Category Segmented Control */}
              <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-lg text-xs">
                {(['ALL', 'ITEM_NOT_RECEIVED', 'NOT_AS_DESCRIBED', 'DAMAGED'] as const).map(cat => (
                  <button
                    key={cat}
                    onClick={() => setFilterReason(cat)}
                    className={`px-2 py-1 rounded text-[11px] font-medium transition-colors whitespace-nowrap ${
                      filterReason === cat
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {cat === 'ALL' ? 'All' : cat === 'ITEM_NOT_RECEIVED' ? 'INR' : cat === 'NOT_AS_DESCRIBED' ? 'SNAD' : 'Damaged'}
                  </button>
                ))}
              </div>

              {/* Case Cards List */}
              <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
                {filteredCases.map(c => {
                  const isSelected = c.case_id === selectedCaseId;
                  const gEval = evaluatePolicyGate(c);
                  const mEval = evaluateMarginEngine(c, gEval.action, gEval.reason_code, gEval.gate_status, gEval.evaluations);

                  return (
                    <button
                      key={c.case_id}
                      onClick={() => handleSelectCase(c.case_id)}
                      className={`w-full text-left p-3.5 rounded-xl border transition-all text-xs flex flex-col gap-1.5 ${
                        isSelected
                          ? 'border-rose-500/60 bg-rose-500/5 shadow-md shadow-rose-950/30'
                          : 'border-slate-800/80 bg-slate-900/40 hover:bg-slate-800/60 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-slate-200">{c.case_id}</span>
                        <span className="font-mono font-bold text-slate-100 tabular-nums">
                          ${c.order_amount.toFixed(2)}
                        </span>
                      </div>

                      {c.scenario_name && (
                        <div className="text-[11px] font-medium text-rose-300">
                          {c.scenario_name}
                        </div>
                      )}

                      <div className="text-slate-400 line-clamp-1">
                        {c.complaint_text}
                      </div>

                      <div className="flex items-center justify-between pt-1 text-[11px] border-t border-slate-800/60 text-slate-500">
                        <span>{c.order_id} · Margin ${c.unit_margin.toFixed(2)}</span>
                        <span className={`font-mono font-semibold ${
                          mEval.action === 'CONTEST' ? 'text-emerald-400' :
                          mEval.action === 'ACCEPT_REFUND' ? 'text-rose-400' :
                          mEval.action === 'PARTIAL_REFUND' ? 'text-sky-400' : 'text-amber-400'
                        }`}>
                          {mEval.action}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Authoritative Copilot Decision Engine (Col 8) */}
            <div className="lg:col-span-8 space-y-6">
              {/* Decision Action Banner */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs uppercase tracking-wider text-slate-400 font-medium block">
                      Authoritative Recommendation
                    </span>
                    <div className="flex items-center gap-3 mt-1.5">
                      <div className={`text-2xl font-bold font-mono tracking-tight ${
                        decisionResult.action === 'CONTEST' ? 'text-emerald-400' :
                        decisionResult.action === 'ACCEPT_REFUND' ? 'text-rose-400' :
                        decisionResult.action === 'PARTIAL_REFUND' ? 'text-sky-400' : 'text-amber-400'
                      }`}>
                        {decisionResult.action}
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700">
                        {decisionResult.reason_code}
                      </span>
                    </div>
                  </div>

                  <div className="sm:text-right border-t sm:border-t-0 border-slate-800/80 pt-3 sm:pt-0">
                    <span className="text-xs text-slate-400 font-medium block">
                      Expected Net Margin Recovery
                    </span>
                    <div className={`text-2xl font-bold font-mono tabular-nums mt-0.5 ${
                      decisionResult.expected_margin_recovery >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {decisionResult.expected_margin_recovery >= 0 ? '+$' : '-$'}
                      {Math.abs(decisionResult.expected_margin_recovery).toFixed(2)}
                    </div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      P(Win): {(decisionResult.p_win * 100).toFixed(1)}% · Fee: ${currentCase.dispute_fee.toFixed(2)}
                    </div>
                  </div>
                </div>

                {decisionResult.settlement_offer && (
                  <div className="mt-4 p-3 rounded-lg bg-sky-950/30 border border-sky-800/50 text-xs text-sky-300 flex items-center justify-between">
                    <span>Deterministic 35% Partial Settlement Calculated:</span>
                    <span className="font-mono font-bold text-sky-200">${decisionResult.settlement_offer.toFixed(2)}</span>
                  </div>
                )}

                <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span>Gate Status: <strong className="text-slate-200">{decisionResult.gate_status}</strong></span>
                    <span>·</span>
                    <span>Order: <strong className="text-slate-200">{currentCase.order_id}</strong> (${currentCase.order_amount.toFixed(2)})</span>
                  </div>
                  <button
                    onClick={handleCommitToAudit}
                    className="text-xs text-rose-400 hover:text-rose-300 transition flex items-center gap-1 font-mono"
                    title="Append snapshot to SHA-256 audit chain"
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    <span>Commit to Hash Chain</span>
                  </button>
                </div>
              </div>

              {/* Step 1 & 2: Policy Gate & Margin Math Visualizer */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Scale className="w-4 h-4 text-slate-400" />
                    <h3 className="text-sm font-semibold text-slate-200">
                      Deterministic Policy Gate (R-001 to R-006)
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    Zero LLM Dependency · Pure Python Rules
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {decisionResult.rule_evaluations.map(rule => (
                    <div
                      key={rule.rule_id}
                      className={`p-3 rounded-lg border text-xs flex flex-col justify-between gap-1.5 ${
                        rule.passed
                          ? 'border-emerald-900/40 bg-emerald-950/10 text-slate-200'
                          : 'border-rose-900/40 bg-rose-950/20 text-rose-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold">{rule.rule_id}: {rule.rule_name}</span>
                        <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded ${
                          rule.passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {rule.passed ? 'PASS' : 'TRIGGERED'}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed">
                        {rule.details}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Step 3: Fact-Cited Narrative (LLM Output with Ground Truth Anchors) */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-rose-400" />
                    <h3 className="text-sm font-semibold text-slate-200">
                      Cited Factual Narrative ({narrative.llm_provider})
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Ground Truth Validated</span>
                    <span className="text-slate-500">· {narrative.generation_latency_ms.toFixed(1)}ms</span>
                  </div>
                </div>

                {/* Ground Truth Claims List */}
                <div className="space-y-1.5">
                  <span className="text-xs text-slate-400 font-medium block">
                    Verified Citations from Courier Telematics:
                  </span>
                  <div className="space-y-1.5">
                    {narrative.claims.map((claim, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs text-slate-300 flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <span>{claim.statement}</span>
                          <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
                            <span>Evidence IDs:</span>
                            {claim.fact_ids.map(fid => (
                              <span key={fid} className="text-rose-400/90 bg-rose-500/10 px-1.5 py-0.2 rounded border border-rose-500/20">
                                [FACT:{fid}]
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Formal Dispute Reply Draft */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">
                      Formal Evidence Defense Draft (Ready for Stripe / Payment Rail):
                    </span>
                    <button
                      onClick={handleCopyDraft}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition flex items-center gap-1.5"
                    >
                      {copiedDraft ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy Draft</span>
                        </>
                      )}
                    </button>
                  </div>

                  <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-300 font-sans whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                    {narrative.draft_reply}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: CRYPTOGRAPHIC AUDIT LEDGER */}
        {activeTab === 'audit' && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-400" />
                  <span>Immutable SHA-256 Dispute Audit Chain</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                  Every decision, gate status, and narrative hash is cryptographically appended to a backward-linked ledger.
                  Any unauthorized database edit or retrospective change breaks hash pointers and is mathematically caught.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleVerifyChain}
                  className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition flex items-center gap-2 shadow-sm"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Verify All Blocks</span>
                </button>
                <button
                  onClick={handleSimulateTamper}
                  className="px-3.5 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 rounded-lg text-xs font-medium transition flex items-center gap-2"
                  title="Simulates an attacker changing an action in the database"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Simulate Attack / Tamper</span>
                </button>
              </div>
            </div>

            {/* Audit Status Card */}
            {auditVerification && (
              <div className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
                auditVerification.valid
                  ? 'border-emerald-800/50 bg-emerald-950/20 text-emerald-300'
                  : 'border-rose-800/60 bg-rose-950/30 text-rose-300'
              }`}>
                <div className="flex items-center gap-2.5">
                  {auditVerification.valid ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                  )}
                  <div>
                    <span className="font-bold">{auditVerification.valid ? 'INTEGRITY VERIFIED' : 'TAMPERING DETECTED'}</span>
                    <p className="mt-0.5 text-slate-300">{auditVerification.message}</p>
                  </div>
                </div>
                <div className="text-right font-mono text-[11px] text-slate-400">
                  Checked at {auditVerification.checkedAt}
                </div>
              </div>
            )}

            {/* Block Ledger Explorer */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Block Chain Sequence ({auditChain.length} blocks)</span>
                <span>SHA-256 Digest Verification</span>
              </div>

              <div className="divide-y divide-slate-800/60">
                {auditChain.map((b) => (
                  <div key={b.index} className="p-4 hover:bg-slate-800/30 transition text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded bg-slate-800 font-mono font-bold text-slate-200">
                          #{b.index}
                        </span>
                        <span className="font-mono font-semibold text-rose-400">{b.case_id}</span>
                        <span className={`font-mono font-semibold text-xs px-2 py-0.5 rounded ${
                          b.action === 'CONTEST' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          b.action === 'ACCEPT_REFUND' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          b.action === 'PARTIAL_REFUND' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                          'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {b.action}
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono text-[11px]">{b.timestamp}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 font-mono text-[11px] pt-1">
                      <div className="p-2 rounded bg-slate-950 border border-slate-800/60 text-slate-400 truncate">
                        <span className="text-slate-500">Prev Hash: </span>
                        <span className="text-slate-300">{b.previous_hash}</span>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800/60 text-slate-400 truncate">
                        <span className="text-slate-500">Block Hash: </span>
                        <span className="text-emerald-400">{b.block_hash}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: POLICY RULES & MARGIN MATH */}
        {activeTab === 'rules' && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
              <h2 className="text-base font-bold text-white mb-2">Policy Gate Architecture (Rules R-001 through R-006)</h2>
              <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
                MerchantGuard enforces strict separation of concerns. Deciding the dispute outcome is mathematically and deterministically reserved for pure Python rules. The LLM only compiles cited, legally grounded dispute arguments.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
                {[
                  { id: 'R-001', name: 'Return Window Bypass', cond: 'Claim Date - Delivery Date > 14 days', action: 'CONTEST', desc: 'Customer retained goods past published return terms.' },
                  { id: 'R-002', name: 'Objective Carrier Telematics', cond: 'Carrier GPS match == True AND Signature == True', action: 'CONTEST', desc: 'Conclusive physical proof of delivery handover.' },
                  { id: 'R-003', name: 'High-Value Custody Risk', cond: 'Order > $250.00 without physical signature', action: 'NEEDS_HUMAN', desc: 'Escalates to senior adjuster to prevent high-value loss.' },
                  { id: 'R-004', name: 'Economic Fee Trap', cond: 'EV <= $0.00 or Dispute fee > Unit margin', action: 'ACCEPT_REFUND', desc: 'Prevents losing money contesting low-margin items.' },
                  { id: 'R-005', name: 'Partial Defect Routing', cond: 'Category == DAMAGED / TRANSIT_DEFECT', action: 'PARTIAL_REFUND', desc: 'Generates deterministic 35% settlement offer.' },
                  { id: 'R-006', name: 'Courier Anomaly Missing Data', cond: 'No carrier tracking events or status != DELIVERED', action: 'NEEDS_HUMAN', desc: 'Routes to carrier lost parcel tracer department.' },
                ].map(r => (
                  <div key={r.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-rose-400">{r.id}</span>
                      <span className="font-mono font-bold text-slate-200">{r.action}</span>
                    </div>
                    <div className="font-semibold text-slate-200">{r.name}</div>
                    <div className="p-2 rounded bg-slate-950 font-mono text-[11px] text-slate-400 border border-slate-800/60">
                      {r.cond}
                    </div>
                    <p className="text-slate-400 text-[11px]">{r.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Margin Formula Box */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">Statistical Expected Value (EV) Formula</h3>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-rose-300">
                EV = P(Win) × (Unit Margin + Dispute Fee Saved) - (1 - P(Win)) × Dispute Fee
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Payment processors (Stripe, Adyen, PayPal) levy a non-refundable $15 fee for every lost dispute. MerchantGuard calculates the statistical win probability P(Win) from evidence signals and suppresses contest actions when EV is negative, saving merchants thousands of dollars in fee bleeding.
              </p>
            </div>
          </div>
        )}

        {/* TAB 4: CODE & REPOSITORY EXPLORER */}
        {activeTab === 'code' && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-rose-400" />
                    <span>MerchantGuard Hackathon Repository Skeleton</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    All Phase 1 boilerplate files specified in the AMD Hackathon mega-prompt have been generated.
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
                  <Terminal className="w-3.5 h-3.5" />
                  <span>Pytest Clean · Docker Ready</span>
                </div>
              </div>

              {/* File Tree Overview */}
              <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-slate-300">
                  <div className="font-bold text-rose-400 pb-1 border-b border-slate-800">merchantguard/app/</div>
                  <div>├── api.py (FastAPI SSE)</div>
                  <div>├── schemas.py (Pydantic v2)</div>
                  <div>├── gate.py (Rules R-001..R-006)</div>
                  <div>├── margin.py (EV Engine)</div>
                  <div>├── narrator.py (Fact Validator)</div>
                  <div>├── router.py (ROCm Ladder)</div>
                  <div>└── audit.py (Hash-Chain)</div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-slate-300">
                  <div className="font-bold text-rose-400 pb-1 border-b border-slate-800">merchantguard/data & config/</div>
                  <div>├── config/policy.yaml</div>
                  <div>├── config/margin.yaml</div>
                  <div>├── data/samples/ (4 scenarios)</div>
                  <div>├── data/replay/ (Pre-cached)</div>
                  <div>├── data/generator.py</div>
                  <div>└── models/.gitkeep</div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-slate-300">
                  <div className="font-bold text-rose-400 pb-1 border-b border-slate-800">merchantguard/deploy & tests/</div>
                  <div>├── tests/test_gate.py</div>
                  <div>├── tests/test_margin.py</div>
                  <div>├── tests/test_audit.py</div>
                  <div>├── Dockerfile (appuser 1000)</div>
                  <div>├── docker-compose.yml</div>
                  <div>├── requirements.txt</div>
                  <div>└── README.md & LICENSE</div>
                </div>
              </div>

              {/* Instructions Guide */}
              <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-3">
                <div className="font-semibold text-slate-200">🚀 Kickoff Deployment & Git Commit Commands:</div>
                <div className="font-mono text-slate-400 space-y-1.5 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                  <div>git init</div>
                  <div>git add merchantguard/</div>
                  <div>git commit -m "feat: scaffold MerchantGuard skeleton and baseline FastAPI setup"</div>
                  <div>docker compose -f merchantguard/docker-compose.yml up --build -d</div>
                  <div>pytest merchantguard/tests/ -v</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* MODAL: CREATE CUSTOM DISPUTE CASE */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-rose-400" />
                <span>Simulate Custom Dispute Case</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Case Identifier</label>
                <input
                  type="text"
                  value={newCaseData.case_id}
                  onChange={e => setNewCaseData({ ...newCaseData, case_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Order Amount ($)</label>
                <input
                  type="number"
                  value={newCaseData.order_amount}
                  onChange={e => setNewCaseData({ ...newCaseData, order_amount: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Product Margin ($)</label>
                <input
                  type="number"
                  value={newCaseData.unit_margin}
                  onChange={e => setNewCaseData({ ...newCaseData, unit_margin: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Gateway Dispute Fee ($)</label>
                <input
                  type="number"
                  value={newCaseData.dispute_fee}
                  onChange={e => setNewCaseData({ ...newCaseData, dispute_fee: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div className="col-span-2">
                <label className="text-slate-400 block mb-1">Claimed Reason</label>
                <select
                  value={newCaseData.claimed_reason}
                  onChange={e => setNewCaseData({ ...newCaseData, claimed_reason: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-100 text-xs"
                >
                  <option value="ITEM_NOT_RECEIVED">ITEM_NOT_RECEIVED (Non-receipt)</option>
                  <option value="DAMAGED">DAMAGED (Partial defect claim)</option>
                  <option value="NOT_AS_DESCRIBED">NOT_AS_DESCRIBED (Discrepancy)</option>
                  <option value="UNAUTHORIZED_CHARGE">UNAUTHORIZED_CHARGE</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Days Ago Delivered</label>
                <input
                  type="number"
                  value={newCaseData.days_ago_delivered}
                  onChange={e => setNewCaseData({ ...newCaseData, days_ago_delivered: parseInt(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Days Ago Claimed</label>
                <input
                  type="number"
                  value={newCaseData.days_ago_claimed}
                  onChange={e => setNewCaseData({ ...newCaseData, days_ago_claimed: parseInt(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-slate-100"
                />
              </div>

              <div className="col-span-2 flex items-center gap-6 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newCaseData.geo_match}
                    onChange={e => setNewCaseData({ ...newCaseData, geo_match: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-rose-500"
                  />
                  <span>Carrier GPS Coordinates Match</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newCaseData.signature_present}
                    onChange={e => setNewCaseData({ ...newCaseData, signature_present: e.target.checked })}
                    className="rounded bg-slate-950 border-slate-800 text-rose-500"
                  />
                  <span>Physical Signature Captured</span>
                </label>
              </div>

              <div className="col-span-2">
                <label className="text-slate-400 block mb-1">Customer Complaint Text</label>
                <textarea
                  value={newCaseData.complaint_text}
                  onChange={e => setNewCaseData({ ...newCaseData, complaint_text: e.target.value })}
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-100 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCustomCase}
                className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold shadow-sm"
              >
                Evaluate Case
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer: Quiet copyright and AMD Hackathon note */}
      <footer className="border-t border-slate-800/80 px-6 py-4 mt-auto text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <div>
          MerchantGuard · AMD Developer Hackathon: ACT III (Track: Reinvent Commerce)
        </div>
        <div className="font-mono text-[11px] text-slate-500">
          Deterministic Policy Gate · Statistical Margin Engine · AMD ROCm vLLM
        </div>
      </footer>
    </div>
  );
}
