# semantic_result.py — unchanged, already clean
from typing import List
from pydantic import BaseModel


class SemanticViolation(BaseModel):
    rule:   str
    reason: str


class SemanticValidationResult(BaseModel):
    safe:            bool
    violations:      List[SemanticViolation] = []
    base_command:    str        # ← add for debugging
    capability:      str | None # ← add for logging