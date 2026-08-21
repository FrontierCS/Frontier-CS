"""Binary-plan rewrite hook used before semijoin-plan lowering."""

from .binary_plan import BinaryJoinNode, LeafNode

Plan = BinaryJoinNode | LeafNode


def rewrite_plan(plan: Plan) -> Plan:
    """Return an equivalent binary plan accepted by the lowering pipeline.

    The optimization policy has been removed for the benchmark. This identity
    implementation preserves the binary-plan-in/binary-plan-out interface.
    """
    return plan
