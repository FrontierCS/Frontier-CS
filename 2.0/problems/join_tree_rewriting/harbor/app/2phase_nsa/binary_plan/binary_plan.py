from __future__ import annotations


class BinaryJoinNode:
    """Join node of a binary join tree.

    # Implementation note:
    The join attributes are stored as integers.
    For example:  R(a,b,c) ⋈ S(a,b,d) joins two relations on attributes a and b.
    Instead of storing the attributes, each attribute is assigned a unique integer id.
    We store the id's instead of the attributes, e.g: {1,2}.
    """

    def __init__(
        self,
        left_child: BinaryJoinNode | LeafNode,
        right_child: BinaryJoinNode | LeafNode,
        join_attributes: set[int],
    ):
        self.left_child = left_child
        self.right_child = right_child
        self.join_attributes = join_attributes
        self.output_schema = left_child.attrs() | right_child.attrs()  # union

    def join_attrs(self) -> set[int]:
        """Returns the join attributes of the join node."""
        return self.join_attributes

    def attrs(self) -> set[int]:
        """Returns the output schema of the join node.
        This is NOT the same as the join attributes!"""
        return self.output_schema

    def __eq__(self, other: BinaryJoinNode) -> bool:
        return (
            isinstance(other, BinaryJoinNode)
            and type(self.left_child) == type(other.left_child)
            and type(self.right_child) == type(other.right_child)
            and self.left_child == other.left_child
            and self.right_child == other.right_child
            and self.join_attributes == other.join_attributes
        )


class LeafNode:
    """Leaf node of a binary join tree."""

    def __init__(self, relation_name: str, attributes: set[int], ec: int):
        self.relation_name = relation_name
        self.attributes = attributes
        self.ec = ec  # estimated cardinality

    def attrs(self) -> set[int]:
        """Returns the attributes of the leaf node."""
        return self.attributes

    def __eq__(self, other: LeafNode) -> bool:
        return (
            isinstance(other, LeafNode)
            and self.relation_name == other.relation_name
            and self.attributes == other.attributes
        )


def is_leaf(node: BinaryJoinNode | LeafNode) -> bool:
    """Returns True if the node is a leaf."""
    return isinstance(node, LeafNode)


def is_join_node(node: BinaryJoinNode | LeafNode) -> bool:
    """Check whether `node` is a join node."""
    return isinstance(node, BinaryJoinNode)


def ll(plan: BinaryJoinNode | LeafNode) -> LeafNode:
    """Get left-most leaf atom of `plan`."""
    if isinstance(plan, LeafNode):
        return plan

    return ll(plan.left_child)


def la(plan: BinaryJoinNode | LeafNode) -> set[int]:
    """Get attributes of left-most leaf atom of `plan`."""
    leftmost_leaf = ll(plan)
    return leftmost_leaf.attrs()


def attrs(plan: BinaryJoinNode | LeafNode) -> set[int]:
    """Get attributes of the plan."""
    if isinstance(plan, LeafNode):
        return plan.attrs()

    return plan.attrs()


def pretty_print(plan: BinaryJoinNode | LeafNode, indent: int = 0) -> str:
    """Returns the plan as a pretty-printed str."""
    if isinstance(plan, LeafNode):
        return indent * " " + f"{plan.relation_name} {plan.attrs()}\n"

    result = f"{' '*indent}JOIN {plan.join_attrs()}, output schema: {plan.attrs()}\n"

    result += pretty_print(plan.left_child, indent + 2)
    result += pretty_print(plan.right_child, indent + 2)

    return result


#######################################################################
# PLAN TRAVERSALS
#######################################################################


def traverse_in_order(plan: BinaryJoinNode | LeafNode):
    """Traverse the plan in-order and yield each node."""
    if isinstance(plan, LeafNode):
        yield plan
    else:
        yield from traverse_in_order(plan.left_child)
        yield plan
        yield from traverse_in_order(plan.right_child)


def traverse_pre_order(plan: BinaryJoinNode | LeafNode):
    """Traverse the plan in pre-order and yield each node."""
    if isinstance(plan, LeafNode):
        yield plan
    else:
        yield plan
        yield from traverse_pre_order(plan.left_child)
        yield from traverse_pre_order(plan.right_child)


def traverse_post_order(plan: BinaryJoinNode | LeafNode):
    """Traverse the plan in post-order and yield each node."""
    if isinstance(plan, LeafNode):
        yield plan
    else:
        yield from traverse_post_order(plan.left_child)
        yield from traverse_post_order(plan.right_child)
        yield plan


#######################################################################
# LEFT-DEEP, RIGHT-DEEP, AND BUSHY PLANS
#######################################################################


def is_left_deep(plan: BinaryJoinNode | LeafNode) -> bool:
    """Check whether `plan` is left-deep."""
    if isinstance(plan, LeafNode):
        return True

    return is_left_deep(plan.left_child) and isinstance(plan.right_child, LeafNode)


def is_right_deep(plan: BinaryJoinNode | LeafNode) -> bool:
    """Check whether `plan` is right-deep."""
    if isinstance(plan, LeafNode):
        return True

    return is_right_deep(plan.right_child) and isinstance(plan.left_child, LeafNode)


def is_bushy(plan: BinaryJoinNode | LeafNode) -> bool:
    """A `plan` is bushy if it is not left-deep and not right-deep."""
    return not is_left_deep(plan) and not is_right_deep(plan)


#######################################################################
# METHODS THAT CHECK CONDITIONS OF A WELL-BEHAVED PLAN
#######################################################################


def node_satisfies_condition_1a(node: BinaryJoinNode | LeafNode) -> bool:
    """
    Check whether condition 1a of a well-behaved plan is satisfied for `node`.
    Condition 1a states: for every interior node P'=(P1 ⋈ P2) in the plan, JA(P') ⊆ LA(P1).
    """
    if isinstance(node, LeafNode):
        return True

    return node.join_attrs().issubset(la(node.left_child))  # JA(P') ⊆ LA(P1)


def node_satisfies_condition_1b(node: BinaryJoinNode | LeafNode) -> bool:
    """
    Check whether condition 1b of a well-behaved plan is satisfied for `node`.
    Condition 1b states: for every interior node P'=(P1 ⋈ P2) in the plan, JA(P') ⊆ LA(P2).
    """
    if isinstance(node, LeafNode):
        return True

    return node.join_attributes.issubset(la(node.right_child))  # JA(P') ⊆ LA(P2)


def check_well_behaved_conditions(plan: BinaryJoinNode | LeafNode) -> tuple[bool, bool]:
    """Check which conditions of a well-behaved plan are satisfied.
    Returns a boolean for each condition: (condition_1a, condition_1b)"""
    satisfies_1a = True
    satisfies_1b = True

    for node in traverse_post_order(plan):  # order does not matter
        satisfies_1a &= node_satisfies_condition_1a(node)
        satisfies_1b &= node_satisfies_condition_1b(node)

    return (satisfies_1a, satisfies_1b)


def is_well_behaved(plan: BinaryJoinNode | LeafNode) -> bool:
    """Check whether `plan` is well-behaved."""
    (satisfies_1a, satisfies_1b) = check_well_behaved_conditions(plan)
    return satisfies_1a and satisfies_1b


#######################################################################
# CHECK FOR CARTESIAN PRODUCTS
#######################################################################


def cartesian_product_free(plan: BinaryJoinNode | LeafNode) -> bool:
    """Check whether the plan is cartesian product free."""
    # TODO
    raise NotImplementedError("TODO: implement cartesian_product_free")
