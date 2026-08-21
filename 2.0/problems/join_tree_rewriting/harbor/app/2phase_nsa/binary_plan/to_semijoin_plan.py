from __future__ import annotations
from .binary_plan import BinaryJoinNode, LeafNode
import json

# Transform a well-behaved binary plan into a semijoin plan.
# If a binary plan is well-behaved, we can simply replace all binary joins by binary semijoins.
#
# In our implemenation, however, the left child of a semijoin cannot be a semijoin itself, but it should be a leaf node.
# Plans for which this is not the case can be represented by means of MULTIsemijoins.
#
# e.g: Consider the left-deep join plan P = (R(ab) ⋈ S(bc)) ⋈ T(ad)
# Because P is well-behaved, the semijoin plan is: (R(ab) ⋉ S(bc)) ⋉ T(ad)
# This is the same as one MULTIsemijoin with guard=R and children=[S,T], and is executed as follows
#     - Build on S and probe from R into S
#     - if result is nonempty, build on T and probe from R⋉S into T

# In-memory representation of a semijoin plan that supports multisemijoins


class MultiSemiJoin:
    def __init__(self, guard: str, children: list[MultiSemiJoin]):
        self.guard = guard
        self.children = children

    def add_child(self, child: MultiSemiJoin):
        self.children.append(child)

    def __eq__(self, other: MultiSemiJoin) -> bool:
        return (
            isinstance(other, MultiSemiJoin)
            and self.guard == other.guard
            and self.children == other.children
        )

    def __str__(self) -> str:
        return f"⋉(guard={self.guard}, children={self.children})"

    @staticmethod
    def from_wellbehaved_plan(plan: BinaryJoinNode | LeafNode) -> MultiSemiJoin:
        """Transform a well-behaved binary plan into a semijoin plan."""
        if isinstance(plan, LeafNode):
            return MultiSemiJoin(guard=plan.relation_name, children=[])

        left = MultiSemiJoin.from_wellbehaved_plan(plan.left_child)
        right = MultiSemiJoin.from_wellbehaved_plan(plan.right_child)
        left.add_child(right)

        return left

    def to_yannakakis_template(self) -> str:
        """Convert the semijoin plan to a string that can be written to a Yannakakis template file."""

        def helper(node: MultiSemiJoin):
            children = [helper(child) for child in node.children]

            return {"guard": node.guard, "children": children}

        semijoin_plan = helper(self)
        result = {"semijoin_plan": semijoin_plan, "replacements": []}
        return json.dumps(result, indent=4)
