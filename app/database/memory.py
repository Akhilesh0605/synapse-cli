"""Behavioral memory management for LLM context injection."""
import logging
from datetime import datetime
from typing import Optional
from app.database.connection import get_db
from app.database.models import BehavioralMemory

logger = logging.getLogger(__name__)


def update_memory(intent: str, shell_type: str, command: str) -> None:
    """
    Upsert intent into BehavioralMemory table.
    
    Args:
        intent: The intent name
        shell_type: The shell type used (e.g., 'powershell', 'bash')
        command: The command executed
    
    Note:
        If intent exists: increment use_count, update last_used_at, update top_command
        If new: insert fresh record
    """
    try:
        with get_db() as session:
            # Try to find existing record
            existing = session.query(BehavioralMemory).filter_by(intent=intent).first()
            
            if existing:
                # Update existing record
                existing.use_count = (existing.use_count or 0) + 1
                existing.last_used_at = datetime.utcnow()
                existing.top_command = command
                session.merge(existing)
            else:
                # Insert new record
                new_memory = BehavioralMemory(
                    intent=intent,
                    shell_type=shell_type,
                    top_command=command,
                    use_count=1,
                    last_used_at=datetime.utcnow(),
                )
                session.add(new_memory)
            
            session.commit()
    except Exception as e:
        logger.debug(f"update_memory error: {str(e)}")


def get_memory_context() -> Optional[dict]:
    """
    Return top 5 most used intents and their dominant shell.
    
    Returns:
        Dictionary with format:
        {
            "top_intents": ["intent1", "intent2", ...],
            "top_shells": ["powershell", "bash", ...],
            "top_commands": ["command1", "command2", ...]
        }
        
        Returns None if no data available.
        
    Note:
        Used by LLM #1 as [MEMORY: {...}] injection in runtime prompt
    """
    try:
        with get_db() as session:
            # Get top 5 most used intents
            top_records = (
                session.query(BehavioralMemory)
                .order_by(BehavioralMemory.use_count.desc())
                .limit(5)
                .all()
            )
            
            if not top_records:
                return None
            
            top_intents = [record.intent for record in top_records if record.intent]
            top_shells = [record.shell_type for record in top_records if record.shell_type]
            top_commands = [record.top_command for record in top_records if record.top_command]
            
            return {
                "top_intents": top_intents,
                "top_shells": top_shells,
                "top_commands": top_commands,
            }
    except Exception as e:
        logger.debug(f"get_memory_context error: {str(e)}")
        return None
