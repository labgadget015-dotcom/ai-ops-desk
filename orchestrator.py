"""AI Ops Desk Orchestrator Service

FastAPI service that coordinates agent execution for incoming messages.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import json
import os
from datetime import datetime
from contextlib import asynccontextmanager

from schemas import WorkflowPayload, Contact, Message, ThreadHistory, TenantConfig
from agents import (
    ingestion_agent,
    triage_agent,
    admin_scheduling_agent,
    support_faq_agent,
    qa_guardrail_agent
)

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ai_ops_desk"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class WorkflowRecord(Base):
    """Workflow persistence model"""
    __tablename__ = "workflows"
    
    workflow_id = Column(String, primary_key=True)
    tenant_id = Column(String, index=True)
    payload = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    status = Column(String)  # pending, processing, completed, failed


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models for API
class IncomingMessageRequest(BaseModel):
    """API request for processing incoming message"""
    tenant_id: str
    source: Dict[str, str]
    contact: Dict[str, Any]
    message: Dict[str, Any]
    tenant_config: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """API response for workflow"""
    workflow_id: str
    decision: Optional[str]
    status: str
    message: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("🚀 AI Ops Desk Orchestrator starting...")
    yield
    print("🛑 AI Ops Desk Orchestrator shutting down...")


# FastAPI app
app = FastAPI(
    title="AI Ops Desk Orchestrator",
    description="Multi-agent AI orchestration for Gmail + Calendar automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_automation_event(event: Dict[str, Any]):
    """Log automation event for observability"""
    # TODO: Implement proper logging (structlog, CloudWatch, etc.)
    print(f"[AUTOMATION_EVENT] {json.dumps(event, default=str)}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "AI Ops Desk Orchestrator",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post("/workflows/incoming-message", response_model=WorkflowResponse)
async def handle_incoming_message(request: IncomingMessageRequest):
    """Process incoming email message through agent pipeline"""
    db = SessionLocal()
    workflow_id = str(uuid.uuid4())
    
    try:
        # Build initial payload
        tenant_config = TenantConfig(
            tenant_id=request.tenant_id,
            **request.tenant_config if request.tenant_config else {}
        )
        
        payload = WorkflowPayload(
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            correlation_id=workflow_id,
            source=request.source,
            contact=Contact(**request.contact),
            message=Message(**request.message),
            thread_history=ThreadHistory(),
            tenant_config=tenant_config
        )
        
        # Store initial workflow
        record = WorkflowRecord(
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            payload=json.loads(json.dumps(payload.__dict__, default=str)),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="processing"
        )
        db.add(record)
        db.commit()
        
        # Run agent pipeline
        agent_logs = []
        
        # 1. Ingestion
        payload, log = ingestion_agent(payload)
        agent_logs.append(log)
        
        # 2. Triage
        payload, log = triage_agent(payload)
        agent_logs.append(log)
        
        # 3. Route to appropriate worker agent
        if payload.classification:
            from schemas import Intent
            
            if payload.classification.intent == Intent.SCHEDULING:
                payload, log = admin_scheduling_agent(payload)
                agent_logs.append(log)
            elif payload.classification.intent == Intent.SUPPORT:
                payload, log = support_faq_agent(payload)
                agent_logs.append(log)
            else:
                agent_logs.append({
                    "agent": "worker",
                    "status": "skipped",
                    "reason": f"No handler for intent: {payload.classification.intent}"
                })
        
        # 4. QA Guardrail (always runs)
        payload, log = qa_guardrail_agent(payload)
        agent_logs.append(log)
        
        # Update workflow record
        record.payload = json.loads(json.dumps(payload.__dict__, default=str))
        record.updated_at = datetime.utcnow()
        record.status = "completed"
        db.commit()
        
        # Log automation event
        log_automation_event({
            "workflow_id": workflow_id,
            "correlation_id": payload.correlation_id,
            "tenant_id": request.tenant_id,
            "agent_logs": agent_logs,
            "decision": payload.qa_decision.value if payload.qa_decision else None,
            "classification": payload.classification.intent.value if payload.classification else None
        })
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            decision=payload.qa_decision.value if payload.qa_decision else None,
            status="completed",
            message="Workflow processed successfully"
        )
        
    except Exception as e:
        # Update workflow as failed
        if 'record' in locals():
            record.status = "failed"
            record.updated_at = datetime.utcnow()
            db.commit()
        
        log_automation_event({
            "workflow_id": workflow_id,
            "status": "failed",
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Workflow processing failed: {str(e)}"
        )
    
    finally:
        db.close()


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Retrieve workflow state for debugging and audit"""
    db = SessionLocal()
    
    try:
        record = db.query(WorkflowRecord).filter_by(
            workflow_id=workflow_id
        ).first()
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return {
            "workflow_id": record.workflow_id,
            "tenant_id": record.tenant_id,
            "status": record.status,
            "payload": record.payload,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat()
        }
    
    finally:
        db.close()


@app.get("/workflows")
async def list_workflows(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List workflows with optional filters"""
    db = SessionLocal()
    
    try:
        query = db.query(WorkflowRecord)
        
        if tenant_id:
            query = query.filter(WorkflowRecord.tenant_id == tenant_id)
        if status:
            query = query.filter(WorkflowRecord.status == status)
        
        records = query.order_by(
            WorkflowRecord.created_at.desc()
        ).limit(limit).all()
        
        return {
            "workflows": [
                {
                    "workflow_id": r.workflow_id,
                    "tenant_id": r.tenant_id,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat()
                }
                for r in records
            ],
            "count": len(records)
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
