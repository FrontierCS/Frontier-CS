# Generates a Yannakakis IR plan from a template.
#
# usage: yannakakis_from_template.py [-h] -t TEMPLATE -b BINARY_JOIN_PLAN

# options:
#   -h, --help            show this help message and exit
#   -t TEMPLATE, --template TEMPLATE
#                         Path to the template file (that contains the semijoin plan)
#   -b BINARY_JOIN_PLAN, --binary_join_plan BINARY_JOIN_PLAN
#                         Path to the binary join plan file
#

from __future__ import annotations


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

    def replace_alias(self, aliases: dict[str, str]):
        """If table name is an alias, replace it with the actual table name.

        Args:
            aliases (dict[str, str]): Mapping of alias to actual table name."""
        if self.table_name in aliases:
            self.table_name = aliases[self.table_name]


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


def generate_semijoin_node(node, replacements):
    if "guard" not in node:
        print(node)
    guard = node["guard"]
    if guard in replacements:
        guard = replacements[guard]
    else:
        guard = {"placeholder": guard}  # FIXME: each semijoin node should have a guard!

    children = []

    for child in node["children"]:
        # convert child to semijoin node and add groupby on top of it.
        groupby = {
            "name": "GROUPBY",
            "group_on": [],
            "child": generate_semijoin_node(child, replacements),
        }
        children.append(groupby)

    return {
        "name": "MULTISEMIJOIN",
        "equijoin_keys": [[] for _ in range(len(children))],
        "guard": guard,
        "children": children,
    }


# Function to recursively find the parent of the topmost HASHJOIN node
def find_parent_of_hashjoin(node, parent=None):
    # If current node is HASHJOIN, return its parent
    if node["name"] == "HASHJOIN":
        return parent

    # Recursively search for HASHJOIN in children
    if "children" in node:
        for child in node["children"]:
            result = find_parent_of_hashjoin(child, node)
            if result:  # If the parent is found, stop the recursion and return
                return result

    raise Exception("Could not find parent of topmost HASHJOIN node")


def collect_equivalence_classes(binary_join_plan) -> EquivalenceClasses:
    equivalence_classes = EquivalenceClasses()

    def helper(node):
        if node["name"] == "HASHJOIN":
            join_on = [
                (
                    Field(cond[0]["table_name"], cond[0]["field_name"]),
                    Field(cond[1]["table_name"], cond[1]["field_name"]),
                )
                for cond in node["condition"]
            ]
            equivalence_classes.update(join_on)

        if "children" in node:
            for child in node["children"]:
                helper(child)

    helper(binary_join_plan["root"])

    return equivalence_classes


def update_groupby_and_equijoinkeys_helper(
    guard_relation: str,
    guard_relation_schema: list[Field],
    child_relation: str,
    child_relation_schema: list[Field],
    groupby_columns: list[int],  # eg: [] --> [0]
    semijoin_keys: list[list[int]],  # eg: [] --> [[1,0]]
    equivalence_classes: EquivalenceClasses,
):
    """Update groupby_columns and semijoin keys"""

    # lookup all equivalence classes that contain both relations
    # this gives us the specific attributes that are equi-joined.
    for equivalence_class in equivalence_classes.classes:
        if any(field.table_name == guard_relation for field in equivalence_class) and any(
            field.table_name == child_relation for field in equivalence_class
        ):
            equijoin = [0, 0]  # PLACEHOLDER

            # now, we have the equi-joined attributes
            # we need to find the positions of these attributes in the schema
            # and fill in the groupby_columns and semijoin_keys accordingly
            for field in equivalence_class:
                if field.table_name == guard_relation:
                    idx = guard_relation_schema.index(field)
                    equijoin[0] = idx
                if field.table_name == child_relation:
                    idx = child_relation_schema.index(field)
                    groupby_columns.append(idx)

            equijoin[1] = len(groupby_columns) - 1
            semijoin_keys.append(equijoin)


def output_schema(semijoin_node) -> list[Field]:
    guard = semijoin_node["guard"]
    schema = find_output_schema(guard)

    return [Field(field["table_name"], field["field_name"]) for field in schema]


def find_relation_name(node):
    if node["name"] == "SEQUENTIALSCAN":
        # return node["relation"]  # ambigious in case of self-joins
        alias = node["projection"][0]["table_name"]
        return alias

    if "children" in node:
        for child in node["children"]:
            result = find_relation_name(child)
            if result:
                return result

    raise Exception("Could not find relation name")


def find_output_schema(node):
    if node["name"] == "PROJECTION":
        return node["on"]
    if node["name"] == "SEQUENTIALSCAN":
        return node["projection"]

    if "children" in node:
        for child in node["children"]:
            result = find_output_schema(child)
            if result:
                return result

    raise Exception("Could not find output schema of relation")


def get_multisemijoins(plan):
    def find_yannakakis_root(node):
        if node["name"] == "YANNAKAKIS":
            return node["root"]

        if "children" in node:
            for child in node["children"]:
                result = find_yannakakis_root(child)
                if result:
                    return result

    def collect_multisemijoins(multisemijoin):
        yield multisemijoin
        for groupby_child in multisemijoin["children"]:
            yield from collect_multisemijoins(groupby_child["child"])

    yann_root = find_yannakakis_root(plan["root"])
    result = list(collect_multisemijoins(yann_root))
    return result


def update_groupby_and_equijoinkeys(plan, equivalence_classes: EquivalenceClasses):
    def helper(semijoin_node, equivalence_classes: EquivalenceClasses):
        guard = semijoin_node["guard"]
        guard_relation = find_relation_name(guard)
        guard_schema = output_schema(semijoin_node)
        groupby_children = semijoin_node["children"]
        equijoin_keys = semijoin_node["equijoin_keys"]
        assert len(equijoin_keys) == len(groupby_children)

        for groupby_child, child_equijoin_keys in zip(groupby_children, equijoin_keys):
            child_relation = find_relation_name(groupby_child["child"]["guard"])
            child_schema = output_schema(groupby_child["child"])
            groupby_columns = groupby_child["group_on"]
            update_groupby_and_equijoinkeys_helper(
                guard_relation,
                guard_schema,
                child_relation,
                child_schema,
                groupby_columns,
                child_equijoin_keys,
                equivalence_classes,
            )

    for multisemijoin in get_multisemijoins(plan):
        helper(multisemijoin, equivalence_classes)


if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--template",
        required=True,
        type=str,
        help="Path to the template file (that contains the semijoin plan)",
    )
    parser.add_argument(
        "-b",
        "--binary_join_plan",
        required=True,
        type=str,
        help="Path to the binary join plan file",
    )

    args = parser.parse_args()

    with open(args.template, "r") as f:
        template = json.load(f)

    with open(args.binary_join_plan, "r") as f:
        binary_join_plan = json.load(f)
        equivalence_classes = collect_equivalence_classes(binary_join_plan)

    # generate yannakakis node from the template

    semijoin_plan = template["semijoin_plan"]
    replacements = template["replacements"]

    yann_plan = {"name": "YANNAKAKIS", "root": generate_semijoin_node(semijoin_plan, replacements)}

    # replace top-most hashjoin node in binary_join_plan with yannakakis node
    parent = find_parent_of_hashjoin(binary_join_plan["root"])
    assert parent is not None, "Could not find parent of topmost HASHJOIN node"
    parent["children"] = [yann_plan]

    # Now, the binary_join_plan is actually the Yannakakis plan
    yannakakis_plan = binary_join_plan

    try:
        # the only missing info is the groupby_columns and semijoin_keys
        update_groupby_and_equijoinkeys(yannakakis_plan, equivalence_classes)
    except Exception as e:
        print(f"{args.template} error while filling in group_on and equijoin_keys: {e}")
    finally:
        # write to output file with the same name as the template file, but with extension .json
        outfile = args.template.replace(".template", ".json")
        with open(outfile, "w") as f:
            f.write(json.dumps(yannakakis_plan, indent=4))

        # print(json.dumps(yannakakis_plan, indent=4))
