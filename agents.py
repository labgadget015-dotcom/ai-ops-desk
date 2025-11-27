"""AI Ops Desk Agent Modules

Each agent is a pure function that takes a WorkflowPayload,
enriches it, and returns the updated payload plus a log dict.
"""

from typing import Tuple, Dict, Any
from datetime import datetime
from schemas import (
    WorkflowPayload,
    Intent,
    Classification,
    Action,
    QADecision,
    Priority
)

# Type alias for agent return value
AgentOutput = Tuple[WorkflowPayload, Dict[str, Any]]


def ingestion_agent(payload: WorkflowPayload) -> AgentOutput:
    """Normalize incoming message and fetch thread history."""
    log = {"agent": "ingestion", "status": "pending"}
    
    try:
        # Fetch thread history from Gmail
        # TODO: Implement fetch_gmail_thread connector
        # thread_history = fetch_gmail_thread(
        #     payload.source["thread_id"],
        #     payload.tenant_config.tenant_id
        # )
        # payload.thread_history = thread_history
        
        log["status"] = "completed"
        log["messages_fetched"] = len(payload.thread_history.messages)
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
    
    payload.updated_at = datetime.utcnow()
    return payload, log


def triage_agent(payload: WorkflowPayload) -> AgentOutput:
    """Classify intent and priority."""
    log = {"agent": "triage", "status": "pending"}
    
    try:
        # TODO: Implement call_llm_triage with actual LLM integration
        # classification = call_llm_triage(
        #     payload.message,
        #     payload.thread_history,
        #     payload.tenant_config
        # )
        
        # Placeholder classification
        classification = Classification(
            intent=Intent.SCHEDULING,
            confidence=0.85,
            priority=Priority.NORMAL
        )
        
        payload.classification = classification
        log["intent"] = classification.intent.value
        log["confidence"] = classification.confidence
        log["status"] = "completed"
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
    
    payload.updated_at = datetime.utcnow()
    return payload, log


def admin_scheduling_agent(payload: WorkflowPayload) -> AgentOutput:
    """For scheduling intents, propose times and draft reply."""
    log = {"agent": "admin_scheduling", "status": "pending"}
    
    # Only run if intent is scheduling
    if payload.classification.intent != Intent.SCHEDULING:
        log["skipped"] = True
        return payload, log
    
    try:
        # TODO: Implement find_calendar_slots and draft_scheduling_reply
        # slots = find_calendar_slots(
        #     payload.tenant_config,
        #     num_slots=3
        # )
        # reply_text = draft_scheduling_reply(
        #     payload.contact.name,
        #     slots,
        #     payload.tenant_config.tone
        # )
        
        # Placeholder
        reply_text = "Thank you for reaching out. Here are some available times..."
        
        action = Action(
            action_type="reply",
            tool_name="gmail",
            tool_args={"body": reply_text}
        )
        payload.action_plan.append(action)
        
        log["slots_proposed"] = 3
        log["status"] = "completed"
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
    
    payload.updated_at = datetime.utcnow()
    return payload, log


def support_faq_agent(payload: WorkflowPayload) -> AgentOutput:
    """For support intents, look up KB and draft answer."""
    log = {"agent": "support_faq", "status": "pending"}
    
    if payload.classification.intent != Intent.SUPPORT:
        log["skipped"] = True
        return payload, log
    
    try:
        # TODO: Implement search_kb and draft_support_answer
        # kb_matches = search_kb(payload.message.body_text, top_k=2)
        # reply_text = draft_support_answer(
        #     payload.message,
        #     kb_matches,
        #     payload.tenant_config.tone
        # )
        
        reply_text = "Based on your question, here is the information..."
        
        action = Action(
            action_type="reply",
            tool_name="gmail",
            tool_args={"body": reply_text}
        )
        payload.action_plan.append(action)
        
        log["kb_matches"] = 2
        log["status"] = "completed"
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
    
    payload.updated_at = datetime.utcnow()
    return payload, log


def qa_guardrail_agent(payload: WorkflowPayload) -> AgentOutput:
    """Evaluate risk and decide auto_send vs draft vs escalate."""
    log = {"agent": "qa_guardrail", "status": "pending"}
    
    try:
        # TODO: Implement score_qa_risk with actual risk scoring
        # risk_score = score_qa_risk(payload, payload.tenant_config)
        
        # Placeholder risk scoring
        risk_score = 0.2
        payload.qa_risk_score = risk_score
        
        # Decide based on intent, confidence, risk, and tenant config
        if (
            payload.classification.confidence < payload.tenant_config.escalation_threshold
            or risk_score > 0.7
        ):
            payload.qa_decision = QADecision.ESCALATE
        elif (
            payload.tenant_config.auto_send_enabled
            and risk_score < 0.3
            and payload.classification.confidence > 0.85
        ):
            payload.qa_decision = QADecision.AUTO_SEND
        else:
            payload.qa_decision = QADecision.DRAFT_ONLY
        
        log["risk_score"] = risk_score
        log["decision"] = payload.qa_decision.value
        log["status"] = "completed"
    except Exception as e:
        log["status"] = "failed"
        log["error"] = str(e)
    
    payload.updated_at = datetime.utcnow()
    return payload, log
