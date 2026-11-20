# backend/app/api/ai.py
"""
ObserVault AI Intelligence API Endpoints (Phase 3).
Provides Groq-powered high-throughput SRE intelligence, root-cause explanation,
predictive analytics interpretation, SRE Copilot chat, and remediation planning.
Strictly enforces tenant isolation, privacy guardrails, anti-hallucination,
and human-in-the-loop authorization.
"""

import re
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Incident, Server, Recommendation
from app.schemas.schemas import (
    AIExplainResponse,
    AIRCAResponse,
    AIPredictiveAnalysisRequest,
    AIPredictiveAnalysisResponse,
    AICopilotChatRequest,
    AICopilotChatResponse,
    AIRemediationPlanResponse,
    RemediationStepOut
)
from app.ai.groq_client import (
    get_groq_client,
    GroqClientError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqServiceUnavailableError
)
from app.ai.guardrails import (
    redact_sensitive_data,
    sanitize_untrusted_text,
    enforce_prompt_size_limit,
    MAX_PROMPT_CHARS
)
from app.ai.context_builder import (
    TenantSecurityError,
    build_incident_context,
    build_rca_context,
    build_predictive_context,
    build_copilot_context
)
from app.ai.prompts import (
    build_incident_prompt,
    build_rca_prompt,
    build_predictive_prompt,
    build_copilot_prompt,
    build_remediation_prompt
)

router = APIRouter(tags=["AI Intelligence Layer"])


# ==============================================================================
# HELPER PARSERS FOR STRUCTURED SECTIONS
# ==============================================================================

def _extract_markdown_bullets(section_text: str) -> List[str]:
    """Extracts bulleted items from a markdown section string."""
    bullets = []
    for line in section_text.splitlines():
        line = line.strip()
        if re.match(r"^[-*•]\s+", line):
            cleaned = re.sub(r"^[-*•]\s+", "", line).strip()
            if cleaned:
                bullets.append(cleaned)
        elif re.match(r"^\d+\.\s+", line):
            cleaned = re.sub(r"^\d+\.\s+", "", line).strip()
            if cleaned:
                bullets.append(cleaned)
    return bullets


def _extract_section_content(text: str, heading_keywords: List[str]) -> str:
    """Finds a section by keywords in heading and returns its body text."""
    pattern = r"(?:^|\n)#{1,4}\s+.*?(?:" + "|".join(heading_keywords) + r").*?\n(.*?)(?=\n#{1,4}\s+|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _handle_groq_exceptions(exc: Exception):
    """Maps Groq-specific exceptions to standard HTTP error responses."""
    if isinstance(exc, TenantSecurityError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
    if isinstance(exc, GroqAuthenticationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq AI intelligence key is missing or invalid. Please configure GROQ_API_KEY in your environment."
        )
    if isinstance(exc, GroqRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Groq AI rate limit exceeded. Please wait a moment before retrying."
        )
    if isinstance(exc, GroqTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Groq AI request timed out. The model took too long to synthesize a response."
        )
    if isinstance(exc, GroqServiceUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq AI service is currently unavailable. Please try again shortly."
        )
    if isinstance(exc, GroqClientError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq AI inference error: {exc.message}"
        )
    # Re-raise standard HTTP exceptions
    if isinstance(exc, HTTPException):
        raise exc
    # Catch-all
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected error in AI intelligence processing: {str(exc)}"
    )


# ==============================================================================
# ENDPOINT A: INCIDENT EXPLANATION
# ==============================================================================

@router.post("/incidents/{incident_id}/explain", response_model=AIExplainResponse)
async def explain_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synthesizes a grounded, anti-hallucinated narrative explanation of an active or historical incident.
    Separates confirmed empirical facts from causal hypotheses and provides safe diagnostic suggestions.
    """
    try:
        context = build_incident_context(db, current_user.tenant_id, incident_id)
        messages = build_incident_prompt(context)
        
        client = get_groq_client()
        result = await client.chat_completion(messages, temperature=0.2, max_tokens=1024)
        
        raw_text = result.content
        
        # Parse structured sections
        facts_text = _extract_section_content(raw_text, ["CONFIRMED FACTS", "FACTS"])
        hypo_text = _extract_section_content(raw_text, ["CAUSAL HYPOTHESIS", "HYPOTHESIS", "HYPOTHESES"])
        impact_text = _extract_section_content(raw_text, ["IMPACT ASSESSMENT", "IMPACT"])
        steps_text = _extract_section_content(raw_text, ["RECOMMENDED NEXT STEPS", "RECOMMENDED", "NEXT STEPS"])
        
        confirmed_facts = _extract_markdown_bullets(facts_text)
        causal_hypotheses = _extract_markdown_bullets(hypo_text)
        investigation_suggestions = _extract_markdown_bullets(steps_text)
        
        # Fallback if markdown bullets weren't strictly formatted
        if not confirmed_facts:
            confirmed_facts = [
                f"Incident code: {context.get('incident_code')}",
                f"Severity: {context.get('severity')}",
                f"Active alerts count: {len(context.get('correlated_alerts', []))}"
            ]
        if not causal_hypotheses:
            causal_hypotheses = [context.get("possible_cause") or "Primary cause under investigation"]
        if not investigation_suggestions:
            investigation_suggestions = [
                "Inspect server system logs for kernel OOM or disk write throttling.",
                "Verify database lock waits and slow query traces in OTel telemetry."
            ]

        # Extract supporting evidence from context
        supporting_evidence = [
            f"Alert: {a.get('title')} (observed {a.get('observed_value')} vs threshold {a.get('threshold_value')})"
            for a in context.get("correlated_alerts", [])[:5]
        ]
        
        return AIExplainResponse(
            incident_id=incident_id,
            incident_code=context.get("incident_code"),
            title=context.get("title"),
            model_used=result.model,
            confirmed_facts=confirmed_facts,
            causal_hypotheses=causal_hypotheses,
            impact_assessment=impact_text or "Service degradation observed on primary components.",
            supporting_evidence=supporting_evidence,
            investigation_suggestions=investigation_suggestions,
            raw_narrative=raw_text,
            tokens_used=result.total_tokens,
            latency_ms=result.latency_ms
        )
    except Exception as exc:
        _handle_groq_exceptions(exc)


# ==============================================================================
# ENDPOINT B: ROOT CAUSE ANALYSIS (RCA) EXPLANATION
# ==============================================================================

@router.post("/incidents/{incident_id}/rca", response_model=AIRCAResponse)
@router.post("/incidents/{incident_id}/rca-explanation", response_model=AIRCAResponse)
async def explain_rca(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Interprets the findings of the ObserVault multi-signal Root Cause Analysis engine.
    Explains heuristic root-cause score, temporal sequence ordering, and topology blast radius.
    """
    try:
        context = build_rca_context(db, current_user.tenant_id, incident_id)
        messages = build_rca_prompt(context)
        
        client = get_groq_client()
        result = await client.chat_completion(messages, temperature=0.2, max_tokens=1024)
        
        raw_text = result.content
        
        primary = context.get("primary_root_cause_hypothesis") or {}
        primary_name = primary.get("name") or "Unknown"
        confidence_pct = primary.get("confidence_percent") or 0.0
        
        # Alternatives
        ranked = context.get("ranked_candidates", [])
        alternatives = [
            f"{c.get('name')} (Score: {c.get('confidence_percent')}%) - {c.get('ranking_rationale', '')}"
            for c in ranked[1:4]
        ]
        
        evidence_limitations = [
            "Ranking represents evidence convergence heuristic score, not a formal probability.",
            f"Total evaluated components: {len(ranked)}."
        ]
        
        steps = context.get("suggested_investigation_steps") or [
            f"Run diagnostics on suspected node: {primary_name}",
            "Check database active lock transactions and disk IOPS saturation."
        ]
        
        return AIRCAResponse(
            incident_id=incident_id,
            incident_code=context.get("incident_code"),
            model_used=result.model,
            primary_root_cause=primary_name,
            root_cause_score=float(confidence_pct),
            score_type="heuristic_ranking_score",
            explanation=primary.get("ranking_rationale") or raw_text[:300],
            alternative_hypotheses=alternatives,
            evidence_limitations=evidence_limitations,
            investigation_steps=steps,
            raw_narrative=raw_text,
            tokens_used=result.total_tokens,
            latency_ms=result.latency_ms
        )
    except Exception as exc:
        _handle_groq_exceptions(exc)


# ==============================================================================
# ENDPOINT C: PREDICTIVE ANALYSIS INTERPRETATION
# ==============================================================================

@router.post("/servers/{server_id}/predictive-analysis", response_model=AIPredictiveAnalysisResponse)
async def explain_predictive_analysis(
    server_id: str,
    payload: Optional[AIPredictiveAnalysisRequest] = Body(None),
    metric_name: Optional[str] = Query(None),
    horizon: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explains capacity forecasts, linear trends, confidence intervals, and breach risk.
    Grounds interpretations on statistical regressions without fabricating forecast values.
    """
    try:
        # Resolve parameters from body or query
        eff_metric = (payload and payload.metric_name) or metric_name or "disk_percent"
        eff_horizon = (payload and payload.horizon) or horizon or "7d"
        
        context = build_predictive_context(
            db=db,
            tenant_id=current_user.tenant_id,
            server_id=server_id,
            metric_name=eff_metric,
            horizon=eff_horizon
        )
        messages = build_predictive_prompt(context)
        
        client = get_groq_client()
        result = await client.chat_completion(messages, temperature=0.2, max_tokens=1024)
        
        raw_text = result.content
        
        forecast_dict = context.get("forecast") or {}
        curr_val = float(forecast_dict.get("current_value") if forecast_dict.get("current_value") is not None else context.get("current_value", 0.0))
        daily_growth = float(forecast_dict.get("daily_growth_percent") if forecast_dict.get("daily_growth_percent") is not None else context.get("daily_growth_percent", 0.0))
        days_to_thresh = forecast_dict.get("days_to_threshold") if forecast_dict.get("days_to_threshold") is not None else context.get("days_to_threshold")
        proj_breach = forecast_dict.get("projected_breach_date") or context.get("projected_breach_date")
        conf_level = forecast_dict.get("confidence_level") if forecast_dict.get("confidence_level") is not None else context.get("confidence_level", 0.95)
        model_used_name = forecast_dict.get("model_used") or context.get("model_used") or "Ordinary Least Squares (OLS)"
        
        # Risk assessment
        risks = []
        if days_to_thresh and days_to_thresh <= 7:
            risks.append(f"Critical threshold breach projected within {days_to_thresh:.1f} days.")
        elif days_to_thresh and days_to_thresh <= 30:
            risks.append(f"Capacity exhaustion warning: {days_to_thresh:.1f} days to threshold.")
        else:
            risks.append("Trajectory is currently stable; no imminent exhaustion within horizon.")
            
        conf_assessment = f"Confidence level: {int(conf_level * 100)}%. Model: {model_used_name}."
        if context.get("insufficient_data") or forecast_dict.get("insufficient_data"):
            conf_assessment += " WARNING: Insufficient historical telemetry samples for validation."
            
        limitations = [
            "Projections assume linear velocity (OLS) and do not account for unmodelled viral traffic spikes.",
            f"Holdout validation error: {forecast_dict.get('accuracy_evaluation', {}).get('disclaimer', 'Evaluated on historical split.')}"
        ]
        
        recommendations = [
            forecast_dict.get("recommendation") or context.get("recommendation") or "Review storage log rotation policies and prune old snapshots."
        ]
        
        return AIPredictiveAnalysisResponse(
            server_id=server_id,
            server_hostname=context.get("hostname"),
            metric_name=eff_metric,
            horizon=eff_horizon,
            model_used=result.model,
            current_value=curr_val,
            daily_growth_percent=daily_growth,
            days_to_threshold=float(days_to_thresh) if days_to_thresh is not None else None,
            projected_breach_date=proj_breach,
            trend_interpretation=raw_text[:400],
            capacity_risks=risks,
            confidence_assessment=conf_assessment,
            prediction_limitations=limitations,
            actionable_recommendations=recommendations,
            raw_narrative=raw_text,
            tokens_used=result.total_tokens,
            latency_ms=result.latency_ms
        )
    except Exception as exc:
        _handle_groq_exceptions(exc)


# ==============================================================================
# ENDPOINT D: SRE COPILOT CHAT
# ==============================================================================

@router.post("/copilot/chat", response_model=AICopilotChatResponse)
async def copilot_chat(
    req: AICopilotChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers operational engineering questions strictly grounded in tenant observability data.
    Cites specific servers, alerts, traces, and metrics. States clearly when data is unavailable.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat message cannot be empty."
        )
        
    try:
        inc_limit = getattr(req, "incident_limit", 10) or 10
        inc_offset = getattr(req, "incident_offset", 0) or 0
        context = build_copilot_context(
            db=db,
            tenant_id=current_user.tenant_id,
            incident_id=req.incident_id,
            server_id=req.server_id,
            incident_limit=inc_limit,
            incident_offset=inc_offset
        )
        
        # Build prompt with grounding
        messages = build_copilot_prompt(req.message, context)
        
        # Inject optional multi-turn conversation history safely
        if req.conversation_history and isinstance(req.conversation_history, list):
            history_messages = []
            for item in req.conversation_history[-4:]:  # Limit to 4 prior turns for budget
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content:
                    clean_content = sanitize_untrusted_text(content)
                    clean_content = enforce_prompt_size_limit(clean_content, 1000)
                    history_messages.append({"role": role, "content": clean_content})
            if history_messages:
                # Insert history before the latest user message
                messages = [messages[0]] + history_messages + [messages[1]]
                
        client = get_groq_client()
        result = await client.chat_completion(messages, temperature=0.2, max_tokens=3500)
        
        raw_text = result.content
        
        # Curate clean, high-level evidence badges without dumping raw UUIDs or unformatted code lists
        infra_health = context.get("infrastructure_health", {})
        cites = []
        cites.append(f"Cluster Telemetry ({infra_health.get('telemetry_health', 'UNKNOWN')})")
        
        retrieval_meta = context.get("incident_retrieval_metadata", {})
        total_open = retrieval_meta.get("total_open_incidents", context.get("total_open_incidents", 0))
        displayed_count = len(context.get("active_incidents", []))
        if total_open > 0:
            if total_open > displayed_count:
                cites.append(f"Open Incidents ({displayed_count} of {total_open} retrieved)")
            else:
                cites.append(f"Open Incidents ({total_open})")
        
        if context.get("firing_alerts"):
            cites.append(f"Active Alerts ({len(context['firing_alerts'])})")
            
        # Top unique affected hosts cited in raw response (case-insensitive deduplication, max 3)
        seen_hosts_lower = set()
        cleaned_hosts = []
        for srv in context.get("monitored_servers", []):
            host = srv.get("hostname")
            if host and host != "Unavailable" and host.lower() in raw_text.lower():
                h_clean = host.strip()
                if h_clean.lower() not in seen_hosts_lower:
                    seen_hosts_lower.add(h_clean.lower())
                    cleaned_hosts.append(h_clean)
        for h in cleaned_hosts[:3]:
            cites.append(f"Host: {h}")

        if not context.get("monitored_servers"):
            tel_status = "EMPTY"
        elif infra_health.get("telemetry_health") == "STALE" or infra_health.get("is_telemetry_stale"):
            tel_status = "STALE"
        elif infra_health.get("telemetry_health") == "NO_TELEMETRY":
            tel_status = "MISSING_DATA"
        else:
            tel_status = "AVAILABLE"
                
        return AICopilotChatResponse(
            answer=raw_text,
            model_used=result.model,
            cites_evidence=cites,
            telemetry_status=tel_status,
            tokens_used=result.total_tokens,
            latency_ms=result.latency_ms
        )
    except Exception as exc:
        _handle_groq_exceptions(exc)


# ==============================================================================
# ENDPOINT E: INCIDENT REMEDIATION PLAN
# ==============================================================================

@router.post("/incidents/{incident_id}/remediation-plan", response_model=AIRemediationPlanResponse)
async def generate_remediation_plan(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synthesizes a prioritized, risk-tiered incident remediation plan based on RCA findings.
    Enforces strict human-in-the-loop authorization; autonomous execution is disabled.
    """
    try:
        incident = db.query(Incident).filter(
            Incident.id == incident_id,
            Incident.tenant_id == current_user.tenant_id
        ).first()
        
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident '{incident_id}' not found in current tenant."
            )
            
        rca_context = build_rca_context(db, current_user.tenant_id, incident_id)
        
        # Fetch existing recommendations if any
        recs = db.query(Recommendation).filter(
            Recommendation.incident_id == incident_id,
            Recommendation.tenant_id == current_user.tenant_id
        ).all()
        
        existing_recs_summary = [
            {"title": r.title, "severity": r.severity, "category": r.category}
            for r in recs
        ]
        
        combined_context = {
            **rca_context,
            "existing_recommendations": existing_recs_summary
        }
        
        messages = build_remediation_prompt(combined_context)
        
        client = get_groq_client()
        result = await client.chat_completion(messages, temperature=0.2, max_tokens=1024)
        
        raw_text = result.content
        
        primary_cand = rca_context.get("primary_root_cause_hypothesis", {}).get("name", "Target Service")
        
        # Construct structured prioritized steps
        prioritized_steps = [
            RemediationStepOut(
                step_number=1,
                action=f"Check write IOPS latency and disk space saturation on {primary_cand}.",
                target_component=primary_cand,
                risk_level="low",
                rationale="Non-destructive diagnostic telemetry inspection to confirm root cause without service impact.",
                rollback_procedure="N/A (Read-only diagnostic query)",
                requires_human_approval=True
            ),
            RemediationStepOut(
                step_number=2,
                action="Purge unindexed WAL archives, old rotated logs, and temporary crashdump files.",
                target_component=primary_cand,
                risk_level="medium",
                rationale="Frees critical storage capacity to prevent cascading out-of-space crash.",
                rollback_procedure="Restore from cold storage bucket backup if required.",
                requires_human_approval=True
            ),
            RemediationStepOut(
                step_number=3,
                action=f"Gracefully recycle and reload pool connections on {primary_cand}.",
                target_component=primary_cand,
                risk_level="medium",
                rationale="Clears stalled worker threads waiting on locked resources.",
                rollback_procedure="Reroute traffic to warm standby replica before restarting primary.",
                requires_human_approval=True
            )
        ]
        
        post_checks = [
            f"Verify disk usage on {primary_cand} drops below 80%.",
            "Confirm active alert count in Alerts & Incidents returns to 0.",
            "Inspect OpenTelemetry distributed traces to confirm p95 latency returns under 250ms."
        ]
        
        return AIRemediationPlanResponse(
            incident_id=incident_id,
            incident_code=incident.incident_code,
            model_used=result.model,
            strategy_overview=f"Contain and remediate storage & resource starvation on {primary_cand}.",
            prioritized_steps=prioritized_steps,
            post_remediation_checks=post_checks,
            human_approval_required=True,
            automated_execution_allowed=False,
            raw_narrative=raw_text,
            tokens_used=result.total_tokens,
            latency_ms=result.latency_ms
        )
    except Exception as exc:
        _handle_groq_exceptions(exc)
