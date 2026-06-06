"""Repository layer for database read/write operations."""
import logging
from typing import Optional
from app.database.connection import get_db
from app.database.models import CommandHistory, PipelineTrace

logger = logging.getLogger(__name__)


def save_command_history(response: dict) -> None:
    """
    Extract from full pipeline response dict and save to database.
    
    Args:
        response: Full pipeline response dictionary
    
    Note:
        Handles missing fields gracefully with .get()
        Never raises - logs errors silently
    """
    try:
        with get_db() as session:
            # Extract fields from response
            request_id = response.get("request_id")
            if not request_id:
                logger.debug("save_command_history: skipping record without request_id")
                return
            
            # Create CommandHistory record
            command_history = CommandHistory(
                request_id=request_id,
                query=response.get("query", ""),
                intent=response.get("intent"),
                action_type=response.get("action_type"),
                shell_type=response.get("shell_type"),
                command=response.get("command"),
                risk_level=response.get("risk_level"),
                status=response.get("status"),
                execution_time_ms=response.get("execution_time_ms"),
                stdout=response.get("stdout"),
                stderr=response.get("stderr"),
                return_code=response.get("return_code"),
            )
            session.add(command_history)
            
            # Save pipeline traces if present
            stages = response.get("pipeline_stages", [])
            for idx, stage in enumerate(stages, 1):
                pipeline_trace = PipelineTrace(
                    request_id=request_id,
                    stage_name=stage.get("name"),
                    stage_order=idx,
                    latency_ms=stage.get("latency_ms"),
                    success=stage.get("success"),
                    error_message=stage.get("error_message"),
                )
                session.add(pipeline_trace)
            
            session.commit()
    except Exception as e:
        logger.debug(f"save_command_history error: {str(e)}")


def get_recent_commands(limit: int = 10) -> list[dict]:
    """
    Return last N commands from CommandHistory.
    
    Args:
        limit: Number of recent commands to return (default: 10)
    
    Returns:
        List of command history dictionaries, most recent first
    """
    try:
        with get_db() as session:
            records = (
                session.query(CommandHistory)
                .order_by(CommandHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            return [record.to_dict() for record in records]
    except Exception as e:
        logger.debug(f"get_recent_commands error: {str(e)}")
        return []


def get_command_by_request_id(request_id: str) -> Optional[dict]:
    """
    Lookup single command by request_id.
    
    Args:
        request_id: The request ID to search for
    
    Returns:
        Command history dictionary if found, None otherwise
    """
    try:
        with get_db() as session:
            record = session.query(CommandHistory).filter_by(request_id=request_id).first()
            return record.to_dict() if record else None
    except Exception as e:
        logger.debug(f"get_command_by_request_id error: {str(e)}")
        return None
