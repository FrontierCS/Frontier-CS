#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// Fast I/O
struct FastIO {
    FastIO() {
        std::ios_base::sync_with_stdio(false);
        std::cin.tie(NULL);
    }
};
FastIO fast_io;

struct Point {
    int x, y;
};

struct Edge {
    int u, v;
};

const int N_VER = 400;
const int M_EDGES = 1995;

Point vertices[N_VER];
Edge edges[M_EDGES];
int euclidean_distances[M_EDGES];

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
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            if (sz[root_i] < sz[root_j]) std::swap(root_i, root_j);
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
        }
    }
};

int main() {
    for (int i = 0; i < N_VER; ++i) {
        std::cin >> vertices[i].x >> vertices[i].y;
    }
    for (int i = 0; i < M_EDGES; ++i) {
        std::cin >> edges[i].u >> edges[i].v;
        double dx = vertices[edges[i].u].x - vertices[edges[i].v].x;
        double dy = vertices[edges[i].u].y - vertices[edges[i].v].y;
        euclidean_distances[i] = static_cast<int>(round(sqrt(dx * dx + dy * dy)));
    }

    DSU dsu(N_VER);

    for (int i = 0; i < M_EDGES; ++i) {
        int l;
        std::cin >> l;

        int u = edges[i].u;
        int v = edges[i].v;
        int root_u = dsu.find(u);
        int root_v = dsu.find(v);

        if (root_u == root_v) {
            std::cout << 0 << std::endl;
        } else {
            int future_bridges_count = 0;
            int min_future_d = 2000; // Larger than max possible distance

            for (int j = i + 1; j < M_EDGES; ++j) {
                int u_j = edges[j].u;
                int v_j = edges[j].v;
                int root_u_j = dsu.find(u_j);
                int root_v_j = dsu.find(v_j);
                if ((root_u_j == root_u && root_v_j == root_v) || (root_u_j == root_v && root_v_j == root_u)) {
                    future_bridges_count++;
                    if (euclidean_distances[j] < min_future_d) {
                        min_future_d = euclidean_distances[j];
                    }
                }
            }

            bool take_edge = false;
            if (future_bridges_count == 0) {
                take_edge = true;
            } else {
                double k = future_bridges_count;
                double threshold = (double)min_future_d * (k + 3.0) / (k + 1.0);
                if (l < threshold) {
                    take_edge = true;
                }
            }

            if (take_edge) {
                std::cout << 1 << std::endl;
                dsu.unite(u, v);
            } else {
                std::cout << 0 << std::endl;
            }
        }
    }

    return 0;
}