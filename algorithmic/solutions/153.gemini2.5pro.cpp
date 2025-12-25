#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

struct DSU {
    std::vector<int> parent;
    std::vector<int> sz;
    DSU(int n) {
        parent.resize(n);
        std::iota(parent.begin(), parent.end(), 0);
        sz.assign(n, 1);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }
    bool unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            if (sz[root_i] < sz[root_j]) std::swap(root_i, root_j);
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
            return true;
        }
        return false;
    }
};

const int N = 400;
const int M = 1995;
const int LOGN = 9; // ceil(log2(400)) is 9

struct Point { int x, y; };
Point coords[N];

struct Edge { int u, v, id; };
Edge initial_edges[M];
int d_vals[M];

struct WeightedEdge { int u, v, w, id; };
std::vector<WeightedEdge> all_weighted_edges;

std::vector<std::pair<int, int>> adj[N];
int depth[N];
int parent[LOGN][N];
int max_w[LOGN][N];

int calculate_d(int u_idx, int v_idx) {
    long long dx = coords[u_idx].x - coords[v_idx].x;
    long long dy = coords[u_idx].y - coords[v_idx].y;
    return round(sqrt(dx * dx + dy * dy));
}

void dfs(int u, int p, int d, int w_edge) {
    depth[u] = d;
    parent[0][u] = p;
    max_w[0][u] = w_edge;
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int w = edge.second;
        if (v != p) {
            dfs(v, u, d + 1, w);
        }
    }
}

void preprocess_lca() {
    dfs(0, 0, 0, 0);
    for (int k = 1; k < LOGN; ++k) {
        for (int i = 0; i < N; ++i) {
            parent[k][i] = parent[k - 1][parent[k - 1][i]];
            max_w[k][i] = std::max(max_w[k - 1][i], max_w[k - 1][parent[k - 1][i]]);
        }
    }
}

int query_max_w(int u, int v) {
    int res = 0;
    if (depth[u] < depth[v]) std::swap(u, v);

    for (int k = LOGN - 1; k >= 0; --k) {
        if (depth[u] - (1 << k) >= depth[v]) {
            res = std::max(res, max_w[k][u]);
            u = parent[k][u];
        }
    }

    if (u == v) return res;

    for (int k = LOGN - 1; k >= 0; --k) {
        if (parent[k][u] != parent[k][v]) {
            res = std::max({res, max_w[k][u], max_w[k][v]});
            u = parent[k][u];
            v = parent[k][v];
        }
    }
    res = std::max({res, max_w[0][u], max_w[0][v]});
    return res;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        std::cin >> coords[i].x >> coords[i].y;
    }
    for (int i = 0; i < M; ++i) {
        std::cin >> initial_edges[i].u >> initial_edges[i].v;
        initial_edges[i].id = i;
        d_vals[i] = calculate_d(initial_edges[i].u, initial_edges[i].v);
        all_weighted_edges.push_back({initial_edges[i].u, initial_edges[i].v, 2 * d_vals[i], i});
    }

    std::sort(all_weighted_edges.begin(), all_weighted_edges.end(), [](const WeightedEdge& a, const WeightedEdge& b){
        return a.w < b.w;
    });

    DSU dsu_mst(N);
    for (const auto& edge : all_weighted_edges) {
        if (dsu_mst.unite(edge.u, edge.v)) {
            adj[edge.u].push_back({edge.v, edge.w});
            adj[edge.v].push_back({edge.u, edge.w});
        }
    }

    preprocess_lca();

    DSU dsu_online(N);
    int num_components = N;
    double alpha_min = 0.8, alpha_max = 2.0;

    for (int i = 0; i < M; ++i) {
        int l;
        std::cin >> l;
        int u = initial_edges[i].u;
        int v = initial_edges[i].v;

        bool take_edge = false;
        if (dsu_online.find(u) != dsu_online.find(v)) {
            if (M - i <= num_components - 1) {
                take_edge = true;
            } else {
                int w_max = query_max_w(u, v);
                double progress = (N > 2) ? std::min(1.0, (double)(N - num_components) / (N - 2.0)) : 0.0;
                double alpha = alpha_min + (alpha_max - alpha_min) * progress;
                if (l < alpha * w_max) {
                    take_edge = true;
                }
            }
        }

        if (take_edge) {
            dsu_online.unite(u, v);
            num_components--;
            std::cout << 1 << std::endl;
        } else {
            std::cout << 0 << std::endl;
        }
    }

    return 0;
}