import os, shutil
from abc import abstractmethod
from copy import deepcopy
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import logging
import stat
from src.utils.constant import get_n_power

class EntryFormat:
    def __init__(self, ruleList: list):
        self.ruleList = ruleList

    def __call__(self, entry: str):
        for rule in self.ruleList:
            match, output = rule(entry)
            if match:
                return {} if output == None else output
        return {}


class EntryRule:
    @abstractmethod
    def __call__(self, entry: str) -> (bool, dict):
        pass


class AlwaysMatchedRule(EntryRule):
    def __call__(self, entry: str) -> (bool, dict):
        return (True, {})

class SkipRule(AlwaysMatchedRule):
    def __call__(self, entry: str) -> (bool, dict):
        return (
            True,
            {
                "entry" : entry,
            }
        )

class AlwaysDismatchedRule(EntryRule):
    def __call__(self, entry: str) -> (bool, dict):
        return (False, {})


class PrefixRule(EntryRule):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self, entry: str) -> (bool, dict):
        return (
            entry.strip().startswith(self.prefix),
            {}
        )


PrefixIgnoreRule = PrefixRule # alias

class PrefixSkipRule(PrefixRule):
    def __call__(self, entry: str) -> (bool, dict):
        return (
            entry.strip().startswith(self.prefix),
            {
                "entry": entry
            }
        )


class RegExRule(EntryRule):
    def __init__(self, regex: str, index_group_pairs: dict):
        self.regex = re.compile(regex)
        self.index_group_pairs = index_group_pairs
    
    def __call__(self, entry: str) -> (bool, dict):
        match = self.regex.search(entry)
        if match == None:
            return (False, {})
        output = {}
        for index, group in self.index_group_pairs.items():
            if group == -1:
                output[index] = entry
            else:
                output[index] = match.group(group)
        return (True, output)


class RuleGroup:
    def __init__(
        self,
        entrance_rule: EntryRule,
        exit_rule: EntryRule,
        ruleList: list,
        dismatch_policy = "exit_rule"
    ):
        self.entrance_rule = entrance_rule
        self.exit_rule = exit_rule
        self.ruleList = ruleList
        self.dismatch_policy = dismatch_policy

    def access(self, entry: str) -> bool:
        return self._enter(entry)

    def _enter(self, entry: str) -> bool:
        return self.entrance_rule(entry)[0]

    def _exit(self, entry: str) -> bool:
        return self.exit_rule(entry)[0]

    def _dismatch(self, entry: str) -> bool:
        def dismatch_policy_exit_rule(entry: str):
            return self._exit(entry)

        def dismatch_policy_exit(entry: str):
            return True 

        def dismatch_policy_stay(entry: str):
            return False

        dismatch_policy_set = {
            "default": dismatch_policy_exit_rule,
            "exit_rule": dismatch_policy_exit_rule,
            "exit": dismatch_policy_exit,
            "stay": dismatch_policy_stay,
        }

        dismatch_policy = dismatch_policy_set.get(
            self.dismatch_policy,
            dismatch_policy_set["default"]
        )

        return dismatch_policy(entry)

    def __call__(self, entry: str):
        for rule in self.ruleList:
            match, output = rule(entry)
            if match:
                return (
                    {} if output == None else output,
                    self._exit(entry)
                )
        
        return (
            {},
            self._dismatch(entry)
        )
        

class EntryFormatWithRuleGroups(EntryFormat):
    def __init__(self, ruleGroups: list):
        self.ruleGroups = ruleGroups
        self._nowGroup = None

    def inGroup(self) -> bool:
        return self._nowGroup != None

    def quitGroup(self):
        self._nowGroup = None

    def __call__(self, entry: str):
        if self._nowGroup == None:
            for ruleGroup in self.ruleGroups:
                if ruleGroup.access(entry):
                    self._nowGroup = ruleGroup
                    break
            else:
                # no available rule group
                return {}
        
        output, exited = self._nowGroup(entry)
        if exited:
            self.quitGroup()
        return output
    
def read_benchmark(database, benchmark_path, args):
    logging.info("read database from benchmark %s" % (benchmark_path))
    database["benchmark_dir"] = benchmark_path
    return read_benchmark_from_def(database, database["benchmark_dir"], args)

def read_benchmark_from_def(database, benchmark_path, args):
    node_info = {}
    node_info_raw_id_name = {}

    node_cnt = 0
    port_info = {}
    standard_cell_name = []
    port_to_net_dict = {}


    database["def_file"] = f"{args.benchmark}.def"

    design_name = os.path.splitext(database["def_file"])[0]

    database["files"] = {
        "def_file": database["def_file"],
        "lef_file": "%s.lef" % design_name,
        "v_file": "%s.v" % design_name
    }

    database["nodes"] = {}
    database["macros"] = []


    read_lef(
        database,
        os.path.join(
            database["benchmark_dir"],
            database["files"]["lef_file"]
        )
    )
    
    read_def(
        database,
        os.path.join(
            database["benchmark_dir"],
            database["files"]["def_file"]
        )
    )

    # compute area each macro type
    macro_type_area = {}
    for macro_type in database["macro_size"]:
        size_x, size_y = database["macro_size"][macro_type]
        area = size_x * size_y
        macro_type_area[macro_type] = area

    # compute area each cell
    cell_area_dict = {}
    cell_total_area = 0
    for cell in database["nodes"]:
        cell_type = database["nodes"][cell]["node_type"]
        area = macro_type_area[cell_type]
        cell_area_dict[cell] = area
        cell_total_area += area
    
    cell_lst = list(cell_area_dict.keys())
    cell_lst = sorted(cell_lst, key=lambda x: cell_area_dict[x], reverse=True)

    n_macro = min(len(cell_lst), args.n_macro)
    
    macro_lst = cell_lst[:n_macro]
    standard_cell_name = cell_lst[n_macro:]


    ratio_x, ratio_y = get_scaling_ratio(database)
    canvas_lx = database["diearea_rect"][0] * ratio_x
    canvas_ly = database["diearea_rect"][1] * ratio_y
    canvas_ux = database["diearea_rect"][2] * ratio_x
    canvas_uy = database["diearea_rect"][3] * ratio_y
    for id, macro in enumerate(macro_lst):
        # scaling
        place_x = eval(database["nodes"][macro]['x']) * ratio_x
        place_y = eval(database["nodes"][macro]['y']) * ratio_y

        macro_type = database["nodes"][macro]["node_type"]
        size_x, size_y = database["macro_size"][macro_type]

        node_info[macro] = {"id": id, "size_x": size_x, "size_y": size_y, "area": size_x * size_y}
        node_info[macro]["raw_x"] = place_x
        node_info[macro]["raw_y"] = place_y
        node_info_raw_id_name[id] = macro


    node_cnt = len(node_info)
    assert node_cnt == n_macro

    v_file = open(os.path.join(database["benchmark_dir"],database["files"]["v_file"]), 'r')
    
    net_info = read_v(v_file, node_info, database)
    net_cnt = len(net_info)

    placedb_info = {
        'node_info' : node_info,
        'node_info_raw_id_name' : node_info_raw_id_name,
        'node_cnt' : node_cnt,
        'port_info' : port_info,
        'net_info' : net_info,
        'net_cnt' : net_cnt,
        'canvas_lx' : canvas_lx,
        'canvas_ly' : canvas_ly,
        'canvas_ux' : canvas_ux,
        'canvas_uy' : canvas_uy, 
        'standard_cell_name' : standard_cell_name,
        'port_to_net_dict' : port_to_net_dict,
        'cell_total_area' : cell_total_area,
    }
    return placedb_info
    

def read_v(fopen, node_info, database):
    net_info = {}
    net_cnt = 0
    flag = 0
    for line in fopen.readlines():
        if 'wire' in line:
            line_ls = line.split(" ")
            net_name = line_ls[1].split(";")[0]
            net_info[net_name] = {}
            net_info[net_name]["nodes"] = {}
            net_info[net_name]["ports"] = {}

        if 'Start cells' in line:
            flag = 1
            continue
        if flag == 1:
            if line == '\n':
                break
            pattern = r"\.(\w+)\((.*?)\)"
            matches = re.findall(pattern=pattern, string=line)
            line_ls = line.split(" ")
            node_type = line_ls[0]
            node_name = line_ls[1]

            for pin_net in matches:
                pin = pin_net[0]
                net = pin_net[1]
                if node_name in node_info.keys() and net in net_info.keys():
                    x_offset, y_offset = database["pin_offset"][node_type][pin]
                    # net_info[net]["nodes"][node_name] = {
                    #     "x_offset": x_offset,
                    #     "y_offset": y_offset,
                    # }

                    # offset from lower left corner -> offset from center
                    net_info[net]["nodes"][node_name] = {
                        "x_offset": x_offset - 0.5 * node_info[node_name]["size_x"],
                        "y_offset": y_offset - 0.5 * node_info[node_name]["size_y"],
                    }

    for net_name in list(net_info.keys()):
        if len(net_info[net_name]["nodes"]) <= 1:
            net_info.pop(net_name)
    for net_name in net_info:
        net_info[net_name]['id'] = net_cnt
        net_cnt += 1
    return net_info

def read_lef(database, lef_file):
    macro_start_rule = RegExRule(
        r"MACRO\s+(\w+)",
        {
            "macro_name": 1,
        }
    )
    macro_or_pin_end_rule = RegExRule(
        r"END\s+(\w+)",
        {
            "macro_name_or_pin_name": 1,
        }
    )
    macro_size_rule = RegExRule(
        r"SIZE\s(\d+(\.\d+)?) BY (\d+(\.\d+)?)",
        {
            "size_x" : 1,
            "size_y" : 3,
        }
    )
    macro_pin_start_rule = RegExRule(
        r"(PIN)\s+(\w+)",
        {
            "pin_start" : 1, 
            "pin_name" : 2,
        }
    )
    macro_pin_offset_rule = RegExRule(
        r"RECT\s(-?\d+(\.\d+)?)\s(-?\d+(\.\d+)?)\s(-?\d+(\.\d+)?)\s(-?\d+(\.\d+)?)",
        {
            'x1' : 1,
            'y1' : 3,
            'x2' : 5,
            'y2' : 7,
        }
    )

    macro_rule_group = RuleGroup(
        macro_start_rule,
        AlwaysDismatchedRule(),
        [
            macro_start_rule,
            macro_or_pin_end_rule,
            macro_size_rule,
            macro_pin_start_rule,
            macro_pin_offset_rule,
            RegExRule(
                r"CLASS\s+(\w+)\s+;",
                {
                    "class": 1,
                }
            ),
            SkipRule()
        ]
    )

    other_rule_group = RuleGroup(
        AlwaysMatchedRule(),
        AlwaysMatchedRule(),
        [
            SkipRule()
        ]
    )

    lef_ent_format = EntryFormatWithRuleGroups(
        [
            macro_rule_group,
            other_rule_group
        ]
    )

    assert lef_file is not None and os.path.exists(lef_file), lef_file
    database["lef_macros"] = {}
    database["lef_origin"] = [[]]
    database["macro_size"] = {}
    database["pin_offset"] = {}
    macro_name = None
    pin_name = None
    pin_flag = False
    with open(lef_file, "r") as f:
        for line in f:
            output = lef_ent_format(line)
            if not lef_ent_format.inGroup():
                database["lef_origin"][-1].append(line)
                continue

            if macro_name is None:
                macro_name = output.get("macro_name", None)
                if macro_name is not None:
                    database["lef_macros"][macro_name] = line
                    database["lef_origin"].append([])
                    database["pin_offset"][macro_name] = {}
                continue
            
            # print(output.keys())
            if "macro_name_or_pin_name" in output.keys():
                if pin_flag:
                    pin_flag = False

                    min_pin_grid_x = np.min(pin_grid_x)
                    max_pin_grid_x = np.max(pin_grid_x)
                    min_pin_grid_y = np.min(pin_grid_y)
                    max_pin_grid_y = np.max(pin_grid_y)
                    pin_name = output["macro_name_or_pin_name"]
                    database["pin_offset"][macro_name][pin_name] = ((min_pin_grid_x + max_pin_grid_x)/2,
                                                                    (min_pin_grid_y + max_pin_grid_y)/2)
                    del pin_grid_x
                    del pin_grid_y
                    pin_flag = False
                else:
                    database["lef_macros"][macro_name] += line
                    if output["macro_name_or_pin_name"] == macro_name:
                        lef_ent_format.quitGroup()
                        macro_name = None
            elif "size_x" in output.keys():
                database["macro_size"][macro_name] = (eval(output['size_x']), eval(output['size_y']))
            elif "class" in output.keys():
                # rule: CLASS (CORE|BLOCK)
                c = output["class"]
                if c == "CORE":
                    database["lef_macros"][macro_name] += line
                else:
                    database["lef_macros"][macro_name] += \
                        line.replace(c, "CORE", 1)
            elif "pin_start" in output.keys():
                pin_flag = True
                pin_grid_x = []
                pin_grid_y = []
            elif "x1" in output.keys():
                if pin_flag:
                    x1, y1 = eval(output["x1"]), eval(output["y1"])
                    x2, y2 = eval(output["x2"]), eval(output["y2"])
                    pin_grid_x.append(x1)
                    pin_grid_x.append(x2)
                    pin_grid_y.append(y1)
                    pin_grid_y.append(y2)
            else:
                # rule: skip
                database["lef_macros"][macro_name] += line
    
    for i in range(len(database["lef_origin"])):
        database["lef_origin"][i] = "".join(database["lef_origin"][i])

def read_def(database, def_file):
    
    
    component_start_rule = RegExRule(
        r"COMPONENTS\s+(\d+)\s*;",
        {
            "num_comps": 1,
        }
    )
    component_end_rule = RegExRule(
        r"END\s+COMPONENTS",
        {}
    )
    design_rule = RegExRule(
        r"\s*DESIGN\s+([a-z_A-Z]+)\s+([a-z_A-Z]+)\s+(\d+\.?\d+)\s*;\s*\n?",
        {
            "entry" : 0,
            "key" : 1,
            "value" : 3,
        }
    )
    diearea_rule = RegExRule(
        r"DIEAREA\s+\(\s*(\d+)\s*(\d+)\s*\)\s*\(\s*(\d+)\s*(\d+)\s*\)\s*;\s*\n?",
        {
            # "entry" : 0,
            "lower_x" : 1,
            "lower_y" : 2,
            "upper_x" : 3,
            "upper_y" : 4,
        }
    )
    row_rule = RegExRule(
        r"ROW\s+coreROW_(\d+)\s+core\s+(\d+)\s+(\d+)\s+N\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(\d+)\s+(\d+)\s+;",
        {
            "id" : 1,
            "row_x" : 2,
            "row_y" : 3,
            "after_do" : 4,
            "after_by" : 5,
            "step_x" : 6,
            "step_y" : 7,
        }
    )
    component_rule_group = RuleGroup(
        component_start_rule,
        component_end_rule,
        [
            component_start_rule,
            component_end_rule,
            RegExRule(
                r"(-)\s+(\w+)\s+(\w+)",
                {
                    "head": 1,
                    "node_name": 2,
                    "node_type": 3,
                }
            ),
            RegExRule(
                r"(\+)\s+(\w+)\s*\(\s*([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*\)\s*(\w+)\s+;",
                {
                    "head": 1,
                    "state": 2,
                    "x": 3,
                    "y": 7,
                    "dir": 11,
                }
            ),
        ]
    )

    other_rule_group = RuleGroup(
        
        AlwaysMatchedRule(),
        AlwaysMatchedRule(),
        [
            design_rule,
            diearea_rule,
            row_rule,
            SkipRule()
        ]
    )

    def_ent_format = EntryFormatWithRuleGroups(
        [
            component_rule_group,
            other_rule_group
        ]
    )

    assert def_file is not None and os.path.exists(def_file)
    database["def_origin"] = [[]]
    database["design_config"] = {}
    database["diearea_rect"] = []
    database["row"] = {}
    with open(def_file, "r") as f:
        for line in f:
            output = def_ent_format(line)
            if output.get("entry", None) is not None:
                entry = output.get("entry")
                database["def_origin"][-1].append("%s" % (entry))
            else:
                database["def_origin"].append([])
            if output == {}:
                continue

            if "num_comps" in output.keys():
                database.update(output)
            elif "key" in output.keys():
                database["design_config"][output["key"]] = eval(output["value"]) 

            elif "lower_x" in output.keys():
                database["diearea_rect"].extend([eval(output['lower_x']), 
                                                eval(output['lower_y']),
                                                eval(output['upper_x']),
                                                eval(output['upper_y'])])
            elif "row_y" in output.keys():
                database["row"][output["id"]] = {}
                database["row"][output["id"]]["row_x"] = int(output["row_x"])
                database["row"][output["id"]]["row_y"] = int(output["row_y"])
                database["row"][output["id"]]["after_do"] = int(output["after_do"])
                database["row"][output["id"]]["after_by"] = int(output["after_by"])
                database["row"][output["id"]]["step_x"] = int(output["step_x"])
                database["row"][output["id"]]["step_y"] = int(output["step_y"])
            else:
                head = output.get("head", None)
                if head == '-':
                    node_name = output["node_name"]
                    database["nodes"][node_name] = deepcopy(output)
                elif head == '+':
                    state = output["state"]
                    if state == "FIXED":
                        database["macros"].append(node_name)
                    database["nodes"][node_name].update(output)
                else:
                    continue
    
    for i in range(len(database["def_origin"])):
        database["def_origin"][i] = "".join(database["def_origin"][i])


def get_scaling_ratio(database):
    design_range_x = database["design_config"]["FE_CORE_BOX_UR_X"] - database["design_config"]["FE_CORE_BOX_LL_X"]
    design_range_y = database["design_config"]["FE_CORE_BOX_UR_Y"] - database["design_config"]["FE_CORE_BOX_LL_Y"]
    diearea_range_x = database["diearea_rect"][2] - database["diearea_rect"][0]
    diearea_range_y = database["diearea_rect"][3] - database["diearea_rect"][1]

    ratio_x = design_range_x / diearea_range_x
    ratio_y = design_range_y / diearea_range_y

    return ratio_x, ratio_y

def get_inv_scaling_ratio(database):
    design_range_x = database["design_config"]["FE_CORE_BOX_UR_X"] - database["design_config"]["FE_CORE_BOX_LL_X"]
    design_range_y = database["design_config"]["FE_CORE_BOX_UR_Y"] - database["design_config"]["FE_CORE_BOX_LL_Y"]
    diearea_range_x = database["diearea_rect"][2] - database["diearea_rect"][0]
    diearea_range_y = database["diearea_rect"][3] - database["diearea_rect"][1]

    ratio_x = diearea_range_x / design_range_x
    ratio_y = diearea_range_y / design_range_y

    return ratio_x, ratio_y
        
def write_def(file_name, macro_pos, placedb):
    content = placedb.to_def(macro_pos=macro_pos)
    with open(file_name, "w") as f:
        f.write(content)
        

    
    
