# Given a template file that looks as follows:

# {
#     "semijoin_plan": {
#         "guard":"t",
#         "children": [
#             {
#                 "guard": "mc", "children": [
#                     {"guard":"mi_idx", "children": [{"guard":"it", "children": []}]},
#                     {"guard":"ct", "children": []}
#                 ]
#             }
#         ]
#     },
#     "replacements": []
# }

# This script will fill in the "replacements" field with info from the binary join plan (in IR format).

import json


# Function to recursively collect non-HASHJOIN children
def collect_hashjoin_inputs(hashjoin_node):
    result = []
    # Check if the node has children
    if "children" in hashjoin_node:
        for child in hashjoin_node["children"]:
            if child["name"] == "HASHJOIN":
                # Recurse into HASHJOIN children
                result.extend(collect_hashjoin_inputs(child))
            else:
                # Collect non-HASHJOIN children
                result.append(child)

    assert len(result) > 0, "HASHJOIN node must have children"

    return result


# Function to find the topmost HASHJOIN node
def find_top_hashjoin(node):
    # If current node is HASHJOIN, return it
    if node["name"] == "HASHJOIN":
        return node

    # Recursively search for HASHJOIN in children
    if "children" in node:
        for child in node["children"]:
            result = find_top_hashjoin(child)
            if result:
                return result

    raise Exception("Could not find topmost HASHJOIN node")


def find_relation_name(node):
    assert node["name"] != "HASHJOIN"

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


# the output of this function is the "replacements" field in the template
def group_inputs_by_relation(inputs: list) -> dict:
    result = {}
    for input in inputs:
        relation = find_relation_name(input)
        assert relation not in result, "An alias cannot appear multiple times"
        result[relation] = input
    return result


def fill_in_replacements(template, binary_join_plan):
    # Find the topmost HASHJOIN node
    top_hashjoin = find_top_hashjoin(binary_join_plan)

    # Collect all non-HASHJOIN children of the topmost HASHJOIN node
    inputs = collect_hashjoin_inputs(top_hashjoin)

    # Group inputs by relation
    replacements = group_inputs_by_relation(inputs)

    template["replacements"] = replacements

    return template


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--template", required=True, help="Path to the template file")
    parser.add_argument(
        "-b",
        "--binary_join_plan",
        required=True,
        help="Path to the binary join plan file in IR format",
    )

    args = parser.parse_args()

    with open(args.template, "r") as f:
        template = json.load(f)

    with open(args.binary_join_plan, "r") as f:
        binary_join_plan = json.load(f)
        binary_join_plan = binary_join_plan["root"]

    filled_template = fill_in_replacements(template, binary_join_plan)

    # overwrite the template file with the filled in template

    with open(args.template, "w") as f:
        f.write(json.dumps(filled_template, indent=4))
