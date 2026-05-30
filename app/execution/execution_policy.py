from typing import Optional

from app.schemas.execution_policy_schema import(
    ExecutionMode,
    ExecutionPolicyResult
)

CAPABILITY_POLICIES = {


    "filesystem.read": {
        "execution_mode": ExecutionMode.NORMAL,
        "timeout_seconds": 10,

        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },



    "filesystem.write": {
        "execution_mode": ExecutionMode.RESTRICTED,
        "timeout_seconds": 20,

        "allow_network": False,
        "allow_filesystem_write": True,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },



    "network.read": {
        "execution_mode": ExecutionMode.RESTRICTED,
        "timeout_seconds": 30,

        "allow_network": True,
        "allow_filesystem_write": False,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },


    "process.write": {
        "execution_mode": ExecutionMode.SANDBOXED,
        "timeout_seconds": 60,

        "allow_network": False,
        "allow_filesystem_write": True,
        "allow_process_spawn": True,

        "sandbox_required": True,
    },

    "container.read": {
        "execution_mode": ExecutionMode.RESTRICTED,
        "timeout_seconds": 30,

        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },

    # -----------------------------------------------------
    # runtime.info
    # -----------------------------------------------------

    "runtime.info": {
        "execution_mode": ExecutionMode.NORMAL,
        "timeout_seconds": 10,

        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },


    "system.info": {
        "execution_mode": ExecutionMode.RESTRICTED,
        "timeout_seconds": 15,

        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_spawn": False,

        "sandbox_required": False,
    },

    # application launch
    "system.launch": {
        "execution_mode": ExecutionMode.NORMAL,
        "timeout_seconds": 15,
        "allow_network": False,
        "allow_filesystem_write": False,
        "allow_process_spawn": True,
        "sandbox_required": False,
    },
}



class ExecutionPolicyEngine:
    """
    Deterministic execution governance engine.

    Responsibilities:
    - derive runtime policies
    - apply capability governance
    - apply risk governance
    - enforce execution contracts
    """

    @classmethod
    def derive_policy(
        cls,
        risk_level: str,
        capability: Optional[str] = None,
    ) -> ExecutionPolicyResult:


        if not capability:

            return ExecutionPolicyResult(
                allowed=False,

                execution_mode=ExecutionMode.RESTRICTED,

                timeout_seconds=1,

                requires_confirmation=True,

                allow_network=False,
                allow_filesystem_write=False,
                allow_process_spawn=False,

                sandbox_required=False,

                dry_run=False,

                governance_reason=(
                    "Capability classification missing."
                ),

                risk_level=risk_level,
                capability=capability,

                policy_source="capability_policy",
            )
        
        config = CAPABILITY_POLICIES.get(capability)

        if not config:

            return ExecutionPolicyResult(
                allowed=False,

                execution_mode=ExecutionMode.RESTRICTED,

                timeout_seconds=1,

                requires_confirmation=True,

                allow_network=False,
                allow_filesystem_write=False,
                allow_process_spawn=False,

                sandbox_required=False,

                dry_run=False,

                governance_reason=(
                    f"Unknown capability: {capability}"
                ),

                risk_level=risk_level,
                capability=capability,

                policy_source="capability_policy",
            )



        execution_mode = config["execution_mode"]

        timeout_seconds = config["timeout_seconds"]

        requires_confirmation = False

        risk_level = risk_level.upper()

        if risk_level == "LOW":

            pass

        elif risk_level == "MEDIUM":

            requires_confirmation = True

            timeout_seconds += 10

        elif risk_level == "HIGH":

            requires_confirmation = True

            timeout_seconds += 20

            # escalate isolation ONLY
            if execution_mode != ExecutionMode.SANDBOXED:
                execution_mode = ExecutionMode.RESTRICTED

        else:

            return ExecutionPolicyResult(
                allowed=False,

                execution_mode=ExecutionMode.RESTRICTED,

                timeout_seconds=1,

                requires_confirmation=True,

                allow_network=False,
                allow_filesystem_write=False,
                allow_process_spawn=False,

                sandbox_required=False,

                dry_run=False,

                governance_reason=(
                    f"Unknown risk level: {risk_level}"
                ),

                risk_level=risk_level,
                capability=capability,

                policy_source="risk_policy",
            )

        return ExecutionPolicyResult(

            allowed=True,

            execution_mode=execution_mode,

            timeout_seconds=timeout_seconds,

            requires_confirmation=requires_confirmation,

            allow_network=config["allow_network"],

            allow_filesystem_write=(
                config["allow_filesystem_write"]
            ),

            allow_process_spawn=(
                config["allow_process_spawn"]
            ),

            sandbox_required=config["sandbox_required"],

            dry_run=(
                execution_mode == ExecutionMode.DRY_RUN
            ),

            governance_reason=None,

            risk_level=risk_level,

            capability=capability,

            policy_source="capability_policy",
        )
        return self