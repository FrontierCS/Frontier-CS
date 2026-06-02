import logging
import datetime
from src.utils.read_benchmark.read_aux import read_benchmark as read_aux
from src.utils.read_benchmark.read_def import read_benchmark as read_def
from src.utils.read_benchmark.read_def import get_inv_scaling_ratio
from src.utils.debug import *

def get_node_to_net_dict(node_info, net_info):
    node_to_net_dict = {}
    for node_name in node_info:
        node_to_net_dict[node_name] = set()
    for net_name in net_info:
        for node_name in net_info[net_name]["nodes"]:
            node_to_net_dict[node_name].add(net_name)
    return node_to_net_dict


class PlaceDB:
    def __init__(self, args) -> None:
        self.args = args
        
        self.read_benchmark()

    
    def read_benchmark(self):
        if self.args.benchmark_type == "aux":
            placedb_info = read_aux(benchmark_path=self.args.benchmark_path, args=self.args)
        elif self.args.benchmark_type == "def":
            self.database = {}
            placedb_info = read_def(database=self.database, benchmark_path=self.args.benchmark_path, args=self.args)
        else:
            logging.error("No such a benchmark type")
            raise NotImplementedError
        
        self.node_info = placedb_info["node_info"]
        self.node_info_raw_id_name = placedb_info["node_info_raw_id_name"]
        self.node_cnt = placedb_info["node_cnt"]
        self.port_info = placedb_info["port_info"]
        self.net_info = placedb_info["net_info"]
        self.net_cnt = placedb_info["net_cnt"]
        self.canvas_lx = placedb_info["canvas_lx"]
        self.canvas_ly = placedb_info["canvas_ly"]
        self.canvas_ux = placedb_info["canvas_ux"]
        self.canvas_uy = placedb_info["canvas_uy"]
        self.standard_cell_name = placedb_info["standard_cell_name"]
        self.port_to_net_dict = placedb_info["port_to_net_dict"]
        self.cell_total_area = placedb_info["cell_total_area"]
        self.node_to_net_dict = get_node_to_net_dict(node_info=self.node_info,
                                                     net_info=self.net_info)
        
        self.canvas_width = self.canvas_ux - self.canvas_lx
        self.canvas_height = self.canvas_uy - self.canvas_ly
        self.macro_lst = list(self.node_info.keys())

        self.macro_area_sum = 0
        for macro in self.node_info:
            size_x = self.node_info[macro]["size_x"]
            size_y = self.node_info[macro]["size_y"]
            self.macro_area_sum += size_x * size_y


    def to_pl(self, macro_pos=None, fix_macro=True) -> str:
        if macro_pos is None:
            macro_pos = {
                macro: (
                    self.node_info[macro]["raw_x"],
                    self.node_info[macro]["raw_y"],
                )
                for macro in self.macro_lst
            }

        content = ""
        content += "UCLA pl 1.0\n"
        content += "# Created\t:\t%s\n\n" % \
            datetime.datetime.now().strftime("%b %d %Y")
        for std_cell in self.standard_cell_name:
            content += "{}\t{}\t{}\t:\tN\n".format(std_cell, 0, 0)

        if fix_macro:
            fixed = "/FIXED"
        else:
            fixed = ""

        for macro in self.macro_lst:
            x, y = macro_pos[macro]
            content += "{}\t{}\t{}\t:\tN {}\n".format(
                macro,
                round(x) + self.canvas_lx,
                round(y) + self.canvas_ly,
                fixed
            )
        return content
    
    def to_def(self, macro_pos=None, fix_macro=True) -> str:
        if macro_pos is None:
            macro_pos = {}
        def_origin = list(reversed(self.database["def_origin"]))

        content = "###############################################################\n"
        content += "#  Generated on\t:\t%s\n" % \
            datetime.datetime.now().strftime("%b %d %Y")
        content += "###############################################################\n"
        
        content += def_origin.pop()
        content += "DIEAREA ( {} {} ) ( {} {} ) ;\n".format(
            *tuple(self.database["diearea_rect"])
        )
        content += def_origin.pop()

        row_id_lst = sorted(self.database["row"].keys(), key=lambda x:int(x))

        for row_id in row_id_lst:
            row_info = self.database["row"][row_id]
            content += \
                "ROW coreROW_{row_id} core {row_x} {row_y} N DO {after_do} BY {after_by} STEP {step_x} {step_y} ;\n".format(row_id=row_id, **row_info)
            content += def_origin.pop()

        content += "COMPONENTS %s ;\n" % (self.database["num_comps"])

        node_list = self.database["nodes"].keys()
        inv_ratio_x, inv_ratio_y = get_inv_scaling_ratio(self.database)
        for node_name in node_list:
            node_info = self.database["nodes"][node_name]
            content += \
                "- %(node_name)s %(node_type)s\n" % node_info
            if node_name in macro_pos.keys():
                x, y = macro_pos[node_name]

                # inv scaling
                x = round(x * inv_ratio_x) + self.canvas_lx
                y = round(y * inv_ratio_y) + self.canvas_ly
                
                status = "FIXED" if fix_macro else "PLACED"

                content += \
                    f"\t+ {status} ( {x} {y} ) {node_info['dir']} ;\n"
            else:
                content += \
                    "\t+ PLACED ( %(x)s %(y)s ) %(dir)s ;\n" % node_info
                
        content += "END COMPONENTS\n"

        while len(def_origin) > 0:
            content += def_origin.pop()

        return content