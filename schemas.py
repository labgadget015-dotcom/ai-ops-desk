from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class Intent(str, Enum):
    SCHEDULING = "scheduling"
    SUPPORT = "support"
    BILLING = "billing"
    LEAD = "lead"
    OTHER = "other"
    SPAM = "spam"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class QADecision(str, Enum):
    AUTO_SEND = "auto_send"
    DRAFT_ONLY = "draft_only"
    ESCALATE = "escalate"


@dataclass
class Contact:
    email: str
    name: Optional[str] = None
    org_id: Optional[str] = None


@dataclass
class Message:
    subject: str
    body_text: str
    body_html: Optional[str] = None
    received_at: datetime
    message_id: str
    thread_id: str


@dataclass
class ThreadHistory:
    messages: List[Message] = field(default_factory=list)


@dataclass
class Classification:
    intent: Intent
    sub_intent: Optional[str] = None
    priority: Priority = Priority.NORMAL
    confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class Action:
    action_type: str  # "reply", "create_event", "create_task", "enrich_lead"
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    result_id: Optional[str] = None
    status: str = "pending"  # "pending", "completed", "failed"


@dataclass
class TenantConfig:
    tenant_id: str
    timezone: str = "Europe/London"
    working_hours_start: int = 9  # hour (0-23)
    working_hours_end: int = 17
    working_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0=Mon
    tone: str = "professional"
    auto_send_enabled: bool = False
    escalation_threshold: float = 0.7  # confidence below this → escalate


@dataclass
class WorkflowPayload:
    workflow_id: str  # UUID
    tenant_id: str
    correlation_id: str  # for distributed tracing

    # Input
    source: Dict[str, str]  # {"channel": "gmail", "thread_id": "...", "message_id": "..."}
    contact: Contact
    message: Message
    thread_history: ThreadHistory
    tenant_config: TenantConfig

    # Enrichment by agents
    classification: Optional[Classification] = None
    qa_decision: Optional[QADecision] = None
    qa_risk_score: Optional[float] = None  # 0.0 to 1.0

    # Actions planned and executed
    action_plan: List[Action] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
