"""SQLAlchemy ORM models for SynapseCLI database."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CommandHistory(Base):
    """Record of executed commands in the pipeline."""
    __tablename__ = "command_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, unique=True, nullable=False, index=True)
    query = Column(Text, nullable=False)
    intent = Column(String)
    action_type = Column(String)
    shell_type = Column(String)
    command = Column(Text)
    risk_level = Column(String)
    status = Column(String)  # success/blocked/error/clarify/require_confirmation
    execution_time_ms = Column(Integer)
    stdout = Column(Text)
    stderr = Column(Text)
    return_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "query": self.query,
            "intent": self.intent,
            "action_type": self.action_type,
            "shell_type": self.shell_type,
            "command": self.command,
            "risk_level": self.risk_level,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PipelineTrace(Base):
    """Record of each stage in the 7-stage pipeline."""
    __tablename__ = "pipeline_trace"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, ForeignKey("command_history.request_id"), nullable=False, index=True)
    stage_name = Column(String, nullable=False)
    stage_order = Column(Integer)
    latency_ms = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "stage_name": self.stage_name,
            "stage_order": self.stage_order,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BehavioralMemory(Base):
    """Behavioral memory of user intents and preferred commands."""
    __tablename__ = "behavioral_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    intent = Column(String, unique=True, nullable=False, index=True)
    shell_type = Column(String)
    top_command = Column(Text)
    use_count = Column(Integer, default=1)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "intent": self.intent,
            "shell_type": self.shell_type,
            "top_command": self.top_command,
            "use_count": self.use_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
