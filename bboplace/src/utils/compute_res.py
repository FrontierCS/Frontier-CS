from src.utils.constant import INF
from src.utils.debug import *

import numpy as np

def comp_res(macro_pos, placedb):
    if len(macro_pos) == 0:
        return INF
    
    hpwl = 0.0
    for net_name in placedb.net_info:
        max_x = 0.0
        min_x = placedb.canvas_width * 1.1
        max_y = 0.0
        min_y = placedb.canvas_height * 1.1
        for macro in placedb.net_info[net_name]["nodes"]:
            size_x = placedb.node_info[macro]["size_x"]
            size_y = placedb.node_info[macro]["size_y"]
            if np.isnan(macro_pos[macro][0]) or np.isnan(macro_pos[macro][1]):
                return INF
            pin_x = macro_pos[macro][0] + size_x / 2 + placedb.net_info[net_name]["nodes"][macro]["x_offset"]
            pin_y = macro_pos[macro][1] + size_y / 2 + placedb.net_info[net_name]["nodes"][macro]["y_offset"]
            max_x = max(pin_x, max_x)
            min_x = min(pin_x, min_x)
            max_y = max(pin_y, max_y)
            min_y = min(pin_y, min_y)
        if min_x <= placedb.canvas_width and min_y <= placedb.canvas_height:
            hpwl_temp = (max_x - min_x) + (max_y - min_y)
        else:
            hpwl_temp = (max_x - min_x) + (max_y - min_y)
        
        if "weight" in placedb.net_info[net_name]:
            hpwl_temp *= placedb.net_info[net_name]["weight"]
        hpwl += hpwl_temp
    return hpwl

def comp_overlap(macro_pos, placedb):
    overlap_area = 0
    macro_lst = list(macro_pos.keys())
    l = len(macro_lst)
    for idx in range(l):
        macro = macro_lst[idx]
        xl, yl = macro_pos[macro]
        xh = placedb.node_info[macro]["size_x"] + xl
        yh = placedb.node_info[macro]["size_y"] + yl
        for i in range(idx+1, l):
            m = macro_lst[i]
            m_xl, m_yl = macro_pos[m]
            m_xh = placedb.node_info[m]["size_x"] + m_xl
            m_yh = placedb.node_info[m]["size_y"] + m_yl
            if m_xh < xl or m_xl > xh or \
               m_yh < yl or m_yl > yh:
                continue
            
            delta_x = min(m_xh, xh) - max(m_xl, xl)
            delta_y = min(m_yh, yh) - max(m_yl, yl)

            if np.isnan(delta_x) or np.isnan(delta_y):
                return 0
            assert delta_x >= 0, (m_xh, xh, m_xl, xl)
            assert delta_y >= 0, (m_yh, yh, m_yl, yl)
            overlap_area += delta_x * delta_y
    
    return overlap_area / placedb.macro_area_sum