#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>
#include <queue>
#include <iomanip>

struct DSU {
    std::vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        std::iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

const int N = 400;
const int M = 1995;

struct Point {
    int x, y;
};

struct Edge {
    int u, v;
};

std::vector<Point> points(N);
std::vector<Edge> edges(M);
std::vector<double> dists(M);

double calculate_distance(int u_idx, int v_idx) {
    double dx = points[u_idx].x - points[v_idx].x;
    double dy = points[u_idx].y - points[v_idx].y;
    return std::round(std::sqrt(dx * dx + dy * dy));
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        std::cin >> points[i].x >> points[i].y;
    }
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].u >> edges[i].v;
        dists[i] = calculate_distance(edges[i].u, edges[i].v);
    }

    DSU dsu(N);
    const double INF = 1e18;

    for (int i = 0; i < M; ++i) {
        int l_i;
        std::cin >> l_i;

        int u = edges[i].u;
        int v = edges[i].v;

        if (dsu.find(u) == dsu.find(v)) {
            std::cout << 0 << std::endl;
            continue;
        }

        std::map<int, int> rep_to_idx;
        std::vector<int> idx_to_rep;
        for (int j = 0; j < N; ++j) {
            int root = dsu.find(j);
            if (rep_to_idx.find(root) == rep_to_idx.end()) {
                int new_idx = idx_to_rep.size();
                rep_to_idx[root] = new_idx;
                idx_to_rep.push_back(root);
            }
        }
        int k = idx_to_rep.size();

        std::map<std::pair<int, int>, double> min_w;
        for (int j = i + 1; j < M; ++j) {
            int r1 = dsu.find(edges[j].u);
            int r2 = dsu.find(edges[j].v);
            if (r1 != r2) {
                int idx1 = rep_to_idx.at(r1);
                int idx2 = rep_to_idx.at(r2);
                if (idx1 > idx2) std::swap(idx1, idx2);
                double w = 2.0 * dists[j];
                auto it = min_w.find({idx1, idx2});
                if (it == min_w.end() || w < it->second) {
                    min_w[{idx1, idx2}] = w;
                }
            }
        }
        
        std::vector<std::vector<std::pair<int, double>>> comp_adj(k);
        for (auto const& [p, w] : min_w) {
            comp_adj[p.first].push_back({p.second, w});
            comp_adj[p.second].push_back({p.first, w});
        }

        int start_node_idx = rep_to_idx.at(dsu.find(u));
        int end_node_idx = rep_to_idx.at(dsu.find(v));
        
        std::vector<double> min_dist(k, INF);
        min_dist[start_node_idx] = 0;
        std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>, std::greater<std::pair<double, int>>> pq;
        pq.push({0, start_node_idx});

        double future_cost = INF;

        while (!pq.empty()) {
            auto [d, curr_idx] = pq.top();
            pq.pop();

            if (d > min_dist[curr_idx]) continue;
            
            if (curr_idx == end_node_idx) {
                future_cost = d;
                break;
            }

            for (auto const& edge : comp_adj[curr_idx]) {
                int neighbor_idx = edge.first;
                double weight = edge.second;
                if (min_dist[curr_idx] + weight < min_dist[neighbor_idx]) {
                    min_dist[neighbor_idx] = min_dist[curr_idx] + weight;
                    pq.push({min_dist[neighbor_idx], neighbor_idx});
                }
            }
        }

        if (l_i < future_cost) {
            std::cout << 1 << std::endl;
            dsu.unite(u, v);
        } else {
            std::cout << 0 << std::endl;
        }
    }

    return 0;
}