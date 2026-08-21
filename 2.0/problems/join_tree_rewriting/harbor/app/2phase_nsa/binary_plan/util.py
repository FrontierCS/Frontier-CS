from __future__ import annotations
from .binary_plan import BinaryJoinNode, LeafNode
import json


class Field:
    """Schema field. Contains optional table name and field name."""

    def __init__(self, table_name: str | None, field_name: str):
        self.table_name = table_name
        self.field_name = field_name

    def __str__(self):
        if self.table_name is None:
            return self.field_name
        return f"{self.table_name}.{self.field_name}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other: Field):
        return self.cmp_qualified(other)

    def __hash__(self) -> int:
        return hash(repr(self))

    def to_json(self):
        return self.__dict__

    @staticmethod
    def from_json(json_data) -> Field:
        return Field(**json_data)

    @staticmethod
    def from_str(field_str: str) -> Field:
        parts = field_str.split(".")
        if len(parts) == 1:
            return Field(None, parts[0])
        return Field(parts[0], parts[1])

    def to_unqualified(self) -> Field:
        """Return a new Field object without the table name."""
        return Field(None, self.field_name)

    def cmp_unqualified(self, other: Field):
        """Compare fields without considering table names."""
        return self.field_name == other.field_name

    def cmp_qualified(self, other: Field):
        """Compare fields considering table names."""
        return self.table_name == other.table_name and self.field_name == other.field_name


class EquivalenceClasses:
    def __init__(self):
        self.classes: list[set[Field]] = []

    def __str__(self) -> str:
        return str(self.classes)

    def __repr__(self) -> str:
        out = ""
        for eq_class in self.classes:
            out += f"\t - {eq_class}\n"
        return out

    def idx_of_class(self, field: Field) -> int | None:
        """Get the index of the equivalence class that contains the given field."""

        for idx, eq_class in enumerate(self.classes):
            if field in eq_class:
                return idx
        return None

    def update(self, join_on: list[tuple[Field, Field]]):
        """Update equivalence classes with a new equijoin condition."""

        if len(join_on) > 1:
            raise NotImplementedError(
                "Join with more than one equijoin condition is not implemented yet."
            )

        left, right = join_on[0]

        left_class_id = self.idx_of_class(left)
        right_class_id = self.idx_of_class(right)

        if left_class_id is None and right_class_id is None:
            # Neither field is in any class, create a new equivalence class
            new_class = {left, right}
            self.classes.append(new_class)
        elif left_class_id is None and right_class_id is not None:
            # Left field is not in any class, add it to the class of the right field
            self.classes[right_class_id].add(left)
        elif left_class_id is not None and right_class_id is None:
            # Right field is not in any class, add it to the class of the left field
            self.classes[left_class_id].add(right)
        else:
            # assertion below is to make type checker happy
            assert left_class_id is not None and right_class_id is not None

            if left_class_id != right_class_id:
                # merge two classes
                left_class = self.classes[left_class_id]
                right_class = self.classes[right_class_id]
                new_class = left_class.union(right_class)

                self.classes[left_class_id] = new_class
                del self.classes[right_class_id]

    def get_equivalence_class(self, field: Field) -> set[Field] | None:
        """Get the equivalence class that contains the given field.
        Returns None if the field is not in any class."""

        for eq_class in self.classes:
            if field in eq_class:
                return eq_class

        return None


def topmost_hashjoin(node):
    if node["name"] == "HASHJOIN":
        return node

    assert len(node["children"]) == 1
    return topmost_hashjoin(node["children"][0])


def collect_equivalence_classes(node, equivalence_classes: EquivalenceClasses):
    if node["name"] == "HASHJOIN":
        condition: list[tuple[Field, Field]] = [
            (
                Field(cond[0]["table_name"], cond[0]["field_name"]),
                Field(cond[1]["table_name"], cond[1]["field_name"]),
            )
            for cond in node["condition"]
        ]

        equivalence_classes.update(condition)

    for child in node["children"]:
        collect_equivalence_classes(child, equivalence_classes)


def parse_leaf(node) -> tuple[str, list[Field], int]:
    """Get relation name, output schema and estimated cardinality (ec)"""
    if node["name"] == "PROJECTION":
        # Projection node does not have an ec, so we use the child's ec
        relname, schema, ec = parse_leaf(node["children"][0])
        projection: list[Field] = [
            Field(field["table_name"], field["field_name"]) for field in node["on"]
        ]
        return relname, projection, ec
    if node["name"] == "FILTER":
        relname, schema, _ = parse_leaf(node["children"][0])
        # filter node should have an ec
        ec = node["estimated_cardinality"]
        assert ec is not None, "Estimated cardinality of a filter node cannot be None"
        return relname, schema, ec
    if node["name"] == "SEQUENTIALSCAN":
        relation = node["relation"]
        schema = [Field(field["table_name"], field["field_name"]) for field in node["projection"]]
        alias = schema[0].table_name.__str__()
        ec = node["estimated_cardinality"]
        return alias, schema, ec

    raise Exception("Invalid leaf node: " + node["name"])


def ir_to_binary_plan(json) -> BinaryJoinNode | LeafNode:
    """Converts an IR plan (as json) to a binary join plan."""

    def helper(node, equivalence_classes: EquivalenceClasses) -> BinaryJoinNode | LeafNode:
        if node["name"] == "HASHJOIN":
            left = helper(node["children"][0], equivalence_classes)
            right = helper(node["children"][1], equivalence_classes)

            # Get join attributes (actually, their equivalence class id)
            condition: list[tuple[Field, Field]] = [
                (
                    Field(cond[0]["table_name"], cond[0]["field_name"]),
                    Field(cond[1]["table_name"], cond[1]["field_name"]),
                )
                for cond in node["condition"]
            ]
            eq_class_ids: set[int] = set()
            for left_field, right_field in condition:
                left_class = equivalence_classes.idx_of_class(left_field)
                right_class = equivalence_classes.idx_of_class(right_field)
                assert (
                    left_class is not None
                ), "Left field of equijoin condition not found in equivalence classes"
                assert (
                    right_class is not None
                ), "Right field of equijoin condition not found in equivalence classes"
                assert left_class == right_class, "Equijoin condition should be on the same class"
                assert (
                    left_class not in eq_class_ids
                ), "Multiple join conditions in a join node should be mapped to a different equijoin class"
                eq_class_ids.add(left_class)

            return BinaryJoinNode(left, right, eq_class_ids)

        else:
            # leaf of join tree
            relation_name, schema, ec = parse_leaf(node)
            # map schema to equivalence class ids
            eq_class_ids = set()
            for field in schema:
                eq_class = equivalence_classes.idx_of_class(field)
                if eq_class is not None:
                    eq_class_ids.add(eq_class)

            return LeafNode(relation_name, eq_class_ids, ec)

    top_hash = topmost_hashjoin(json["root"])
    equivalence_classes = EquivalenceClasses()
    collect_equivalence_classes(top_hash, equivalence_classes)
    return helper(top_hash, equivalence_classes)


def ir_file_to_binary_plan(infile: str) -> BinaryJoinNode | LeafNode:
    """Read IR plan from a JSON file and convert it to a binary join plan."""
    with open(infile) as f:
        ir = json.load(f)
    return ir_to_binary_plan(ir)
