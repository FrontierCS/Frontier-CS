import math
import numpy as np
import logging

from .basic_placer import BasicPlacer
from src.utils.constant import INF
from src.utils.debug import *

class MaskGuidedOptimizationPlacer(BasicPlacer):
    def __init__(self, args, placedb) -> None:
        super(MaskGuidedOptimizationPlacer, self).__init__(args=args, placedb=placedb)

        self.n_grid_x = args.n_grid_x
        self.n_grid_y = args.n_grid_y
        self.canvas_width  = placedb.canvas_width
        self.canvas_height = placedb.canvas_height

        self.grid_width  = self.canvas_width / self.n_grid_x
        self.grid_height = self.canvas_height / self.n_grid_y
        
        self.ranked_macro = self._rank_macro()

        # scale size_x, size_y
        self.scale_size = {}
        for macro in self.ranked_macro:
            size_x = self.placedb.node_info[macro]["size_x"]
            size_y = self.placedb.node_info[macro]["size_y"]
            scaled_size_x = math.ceil(size_x / self.grid_width)
            scaled_size_y = math.ceil(size_y / self.grid_height)
            self.scale_size[macro] = {}
            self.scale_size[macro]["size_x"] = scaled_size_x
            self.scale_size[macro]["size_y"] = scaled_size_y
    
    def _genotype2phenotype(self, x):
        # get x_id, y_id for all macro based on genotype x
        macro_grid_pos = {}
        for idx, macro_name in zip(range(0, self.placedb.node_cnt), self.placedb.macro_lst):
            x_id = x[idx]
            y_id = x[idx + self.placedb.node_cnt]
            macro_grid_pos[macro_name] = (math.floor(x_id), math.floor(y_id))

        # greedy search legal grid location
        placed_macro_grid_pos = {}
        hpwl_info_for_each_net = {}
        hpwl = 0.0
        for macro in self.ranked_macro:
            size_x = self.placedb.node_info[macro]["size_x"]
            size_y = self.placedb.node_info[macro]["size_y"]
            scaled_size_x = self.scale_size[macro]["size_x"]
            scaled_size_y = self.scale_size[macro]["size_y"]

            position_mask = np.ones(shape=(self.n_grid_x, self.n_grid_y)) * INF
            position_mask[:self.n_grid_x - scaled_size_x, :self.n_grid_y - scaled_size_y] = 1
            wire_mask = np.ones(shape=(self.n_grid_x, self.n_grid_y)) * 0.1

            for placed_macro in placed_macro_grid_pos:
                l_scaled_x = max(0, placed_macro_grid_pos[placed_macro][0] - scaled_size_x + 1)
                l_scaled_y = max(0, placed_macro_grid_pos[placed_macro][1] - scaled_size_y + 1)
                u_scaled_x = min(self.n_grid_x, placed_macro_grid_pos[placed_macro][0] + self.scale_size[placed_macro]["size_x"])
                u_scaled_y = min(self.n_grid_y, placed_macro_grid_pos[placed_macro][1] + self.scale_size[placed_macro]["size_y"])

                position_mask[l_scaled_x : u_scaled_x, l_scaled_y: u_scaled_y] = INF

            available_scale_x = np.where(position_mask == 1)[0]
            available_scale_y = np.where(position_mask == 1)[1]
            if len(available_scale_x) == 0:
                logging.info("No legal place for macro, return empty macro_pos")
                return {}

            # get wire mask
            for net_name in self.placedb.node_to_net_dict[macro]:
                if net_name in hpwl_info_for_each_net:
                    net_info = hpwl_info_for_each_net[net_name]
                    x_offset = self.placedb.net_info[net_name]["nodes"][macro]["x_offset"] + 0.5 * size_x
                    y_offset = self.placedb.net_info[net_name]["nodes"][macro]["y_offset"] + 0.5 * size_y

                    # Precompute conditions and values outside the loop
                    x_grid = np.arange(self.n_grid_x) * self.grid_width + x_offset
                    y_grid = np.arange(self.n_grid_y) * self.grid_height + y_offset

                    x_min_diff = np.clip(net_info["x_min"] - x_grid, 0, None)
                    x_max_diff = np.clip(x_grid - net_info["x_max"], 0, None)
                    y_min_diff = np.clip(net_info["y_min"] - y_grid, 0, None)
                    y_max_diff = np.clip(y_grid - net_info["y_max"], 0, None)

                    # Update wire_mask using broadcasting
                    wire_mask += np.add.outer(x_min_diff + x_max_diff, np.zeros(self.n_grid_y))
                    wire_mask += np.add.outer(np.zeros(self.n_grid_x), y_min_diff + y_max_diff)

            mask = np.multiply(wire_mask, position_mask)
            min_ele = np.min(mask)
            hpwl += min_ele
            
            available_scale_x = list(np.where(mask == min_ele)[0])
            available_scale_y = list(np.where(mask == min_ele)[1])
            available_scale_coor = list(zip(available_scale_x, available_scale_y))
            available_scale_coor_array = np.array(available_scale_coor)

            grid_size_array = np.array([self.grid_width, self.grid_height])
            grid_pos = np.array(macro_grid_pos[macro])

            dis_array = np.linalg.norm(np.multiply(available_scale_coor_array - grid_pos, grid_size_array), axis=1, ord=1)
            chosen_idx = np.argmin(dis_array)
            chosen_scale_x = available_scale_coor[chosen_idx][0]
            chosen_scale_y = available_scale_coor[chosen_idx][1]

            placed_macro_grid_pos[macro] = (chosen_scale_x, chosen_scale_y)

            center_x = self.grid_width * chosen_scale_x + 0.5 * size_x
            center_y = self.grid_height * chosen_scale_y + 0.5 * size_y
            
            for net_name in self.placedb.node_to_net_dict[macro]:
                x_offset = self.placedb.net_info[net_name]["nodes"][macro]["x_offset"]
                y_offset = self.placedb.net_info[net_name]["nodes"][macro]["y_offset"]
                pin_x = center_x + x_offset
                pin_y = center_y + y_offset
                if net_name not in hpwl_info_for_each_net.keys():
                    hpwl_info_for_each_net[net_name] = {
                        "x_max" : pin_x, "x_min" : pin_x,
                        "y_max" : pin_y, "y_min" : pin_y,
                    }
                else:
                    if hpwl_info_for_each_net[net_name]["x_max"] < pin_x:
                        hpwl_info_for_each_net[net_name]["x_max"] = pin_x
                    elif hpwl_info_for_each_net[net_name]["x_min"] > pin_x:
                        hpwl_info_for_each_net[net_name]["x_min"] = pin_x
                    if hpwl_info_for_each_net[net_name]["y_max"] < pin_y:
                        hpwl_info_for_each_net[net_name]["y_max"] = pin_y
                    elif hpwl_info_for_each_net[net_name]["y_min"] > pin_y:
                        hpwl_info_for_each_net[net_name]["y_min"] = pin_y
            
        # unscale
        macro_pos = {}
        for macro in placed_macro_grid_pos:
            scaled_x, scaled_y = placed_macro_grid_pos[macro]
            x = scaled_x * self.grid_width 
            y = scaled_y * self.grid_height
            macro_pos[macro] = (x, y)

        return macro_pos

    def _rank_macro(self):
        macro_lst = self.placedb.macro_lst.copy()
        net_lst = list(self.placedb.net_info.keys()).copy()

        # compute macro area per net
        for net_name in net_lst:
            area_sum = 0
            for macro in self.placedb.net_info[net_name]["nodes"].keys():
                area_sum += self.placedb.node_info[macro]["area"]
            self.placedb.net_info[net_name]["area"] = area_sum
        # compute area sum per macro
        for macro in macro_lst:
            self.placedb.node_info[macro]["area_sum"] = 0
            for net_name in net_lst:
                if macro in self.placedb.net_info[net_name]["nodes"].keys():
                    self.placedb.node_info[macro]["area_sum"] += self.placedb.net_info[net_name]["area"]

        macro_lst.sort(key=lambda x: self.placedb.node_info[x][self.args.rank_key], reverse=True)
        return macro_lst

    
