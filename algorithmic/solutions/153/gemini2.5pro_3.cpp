#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// Disjoint Set Union with union-by-size and path compression
struct DSU {
    std::vector<int> parent;
    std::vector<int> sz;
    int components;

    DSU(int n) {
        parent.resize(n);
        std::iota(parent.begin(), parent.end(), 0);
        sz.assign(n, 1);
        components = n;
    }

    // Default copy constructor is sufficient and correct
    DSU(const DSU& other) = default;

    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }

    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            if (sz[root_i] < sz[root_j]) std::swap(root_i, root_j);
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
            components--;
        }
    }
};

struct Point {
    int x, y;
};

struct Edge {
    int u, v;
    int d; // Rounded Euclidean distance
};

// Edge in the component graph
struct CompEdge {
    int u, v; // component roots
    double w; // estimated weight

    bool operator<(const CompEdge& other) const {
        return w < other.w;
    }
};

double euclidean_dist(const Point& a, const Point& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return std::sqrt(static_cast<double>(dx * dx + dy * dy));
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const int N = 400;
    const int M = 1995;

    std::vector<Point> ps(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> ps[i].x >> ps[i].y;
    }

    std::vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].u >> edges[i].v;
        edges[i].d = std::round(euclidean_dist(ps[edges[i].u], ps[edges[i].v]));
    }

    DSU dsu(N);

    for (int i = 0; i < M; ++i) {
        int l;
        std::cin >> l;

        int u = edges[i].u;
        int v = edges[i].v;

        int root_u = dsu.find(u);
        int root_v = dsu.find(v);

        if (root_u == root_v) {
            std::cout << 0 << std::endl;
            continue;
        }

        // Dynamically adjust beta based on progress
        double progress = static_cast<double>(i) / (M - 1);
        double beta = 1.4 + 1.6 * progress * progress;

        std::vector<CompEdge> comp_edges;
        if (i < M - 1) {
            comp_edges.reserve(M - 1 - i);
        }
        for (int j = i + 1; j < M; ++j) {
            int fu = dsu.find(edges[j].u);
            int fv = dsu.find(edges[j].v);
            if (fu != fv) {
                comp_edges.push_back({fu, fv, beta * edges[j].d});
            }
        }

        std::sort(comp_edges.begin(), comp_edges.end());

        double w_path = 1e18; // Effectively infinity

        if (!comp_edges.empty()) {
            DSU comp_dsu = dsu;
            for (const auto& edge : comp_edges) {
                if (comp_dsu.find(edge.u) != comp_dsu.find(edge.v)) {
                    comp_dsu.unite(edge.u, edge.v);
                    if (comp_dsu.find(root_u) == comp_dsu.find(root_v)) {
                        w_path = edge.w;
                        break;
                    }
                }
            }
        }
        
        if (static_cast<double>(l) < w_path) {
            std::cout << 1 << std::endl;
            dsu.unite(u, v);
        } else {
            std::cout << 0 << std::endl;
        }
    }

    return 0;
}