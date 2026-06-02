import numpy as np
import igraph as ig
import copy

from .basic_placer import BasicPlacer
from src.utils.debug import *

class SPPlacer(BasicPlacer):
    def __init__(self, args, placedb) -> None:
        super(SPPlacer, self).__init__(args=args, placedb=placedb)

        self.node_cnt = placedb.node_cnt

    def _genotype2phenotype(self, x):
        raw_sequence1 = x[:self.node_cnt]
        raw_sequence2 = x[self.node_cnt:]

        sequence1 = np.argsort(raw_sequence1)
        sequence2 = np.argsort(raw_sequence2)

        source_id = self.node_cnt
        hor_graph = ig.Graph(directed=True)
        ver_graph = ig.Graph(directed=True)
        hor_graph.add_vertices(self.node_cnt + 1)
        ver_graph.add_vertices(self.node_cnt + 1)

        hor_edges = [(source_id, i) for i in range(self.node_cnt)]
        ver_edges = copy.copy(hor_edges)

        for i in range(self.node_cnt):
            for j in range(self.node_cnt):
                if i == j:
                    continue
                if sequence2[i] < sequence2[j]:
                    if sequence1[i] < sequence1[j]:
                        hor_edges.append((i, j))
                    else:
                        ver_edges.append((i, j))

        hor_graph.add_edges(hor_edges)
        del hor_edges
        hor_order = hor_graph.topological_sorting()
        
        d_hor = [0] * (self.node_cnt + 1)
        interval_hor = self.placedb.canvas_width / 1000
        for v in hor_order:
            predecessors = hor_graph.predecessors(v)
            for u in predecessors:
                size = 0 if u == self.node_cnt else self.placedb.node_info[self.placedb.macro_lst[u]]["size_x"]
                d_hor[v] = max(d_hor[v], d_hor[u] + size + interval_hor)
        del hor_graph
        del hor_order

        ver_graph.add_edges(ver_edges)
        interval_ver = self.placedb.canvas_height / 1000
        del ver_edges
        ver_order = ver_graph.topological_sorting()
        
        d_ver = [0] * (self.node_cnt + 1)
        for v in ver_order:
            for u in ver_graph.predecessors(v):
                size = 0 if u == self.node_cnt else self.placedb.node_info[self.placedb.macro_lst[u]]["size_y"]
                d_ver[v] = max(d_ver[v], d_ver[u] + size + interval_ver)

        del ver_graph
        del ver_order

        assert len(d_hor) == len(d_ver)
        macro_pos = {}
        for i in range(self.node_cnt):
            macro = self.placedb.macro_lst[i]
            dis_x = d_hor[i]
            dis_y = d_ver[i]
            macro_pos[macro] = (dis_x, dis_y)
        
        return macro_pos
        
        


        
