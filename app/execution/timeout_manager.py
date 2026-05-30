from app.schemas.execution_policy_schema import ExecutionPolicyResult



TIMEOUT_BY_RISK = {
    "LOW": 10,
    "MEDIUM": 30,
    "HIGH": 60,
}


class TimeoutManager:
    """
    Centralized runtime timeout governance.

    Responsibilities:
    - resolve execution timeouts
    - enforce timeout boundaries
    - centralize timeout policies
    - validate execution duration limits
    """

    MIN_TIMEOUT = 1

    DEFAULT_TIMEOUT = 10

    MAX_TIMEOUT = 300


    @classmethod
    def resolve_timeout(
        cls,
        policy,
    ) -> int:
        """
        Resolve timeout from a full execution policy or fallback to risk-based timeout.
        """
        # Try to get timeout_seconds from policy, else fallback to risk-based
        timeout = None
        if hasattr(policy, 'timeout_seconds') and getattr(policy, 'timeout_seconds', None) is not None:
            timeout = getattr(policy, 'timeout_seconds')
        elif hasattr(policy, 'risk_level'):
            # Try to use risk_level if present
            risk = getattr(policy, 'risk_level', 'LOW')
            timeout = TIMEOUT_BY_RISK.get(risk.upper(), cls.DEFAULT_TIMEOUT)
        else:
            timeout = cls.DEFAULT_TIMEOUT

        return max(
            cls.MIN_TIMEOUT,
            min(timeout, cls.MAX_TIMEOUT)
        )

    @classmethod
    def resolve_by_risk(
        cls,
        risk_level: str,
    ) -> int:
        """
        Legacy timeout resolution from risk level.

        Prefer:
            resolve_timeout(policy)
        """

        risk_level = risk_level.upper()

        timeout = TIMEOUT_BY_RISK.get(
            risk_level,
            cls.DEFAULT_TIMEOUT
        )

        return max(
            cls.MIN_TIMEOUT,
            min(timeout, cls.MAX_TIMEOUT)
        )

    @classmethod
    def is_within_limit(
        cls,
        execution_time_ms: int,
        policy: ExecutionPolicyResult,
    ) -> bool:
        """
        Validate whether execution stayed within
        the allowed timeout window.
        """

        allowed_ms = cls.resolve_timeout(policy) * 1000

        return execution_time_ms <= allowed_ms