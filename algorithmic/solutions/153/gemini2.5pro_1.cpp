#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

const int N = 400;
const int M = 1995;

struct Point {
    int x, y;
};

struct Edge {
    int u, v;
};

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
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::vector<Point> coords(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> coords[i].x >> coords[i].y;
    }

    std::vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].u >> edges[i].v;
    }

    std::vector<long long> d(M);
    for (int i = 0; i < M; ++i) {
        long long dx = coords[edges[i].u].x - coords[edges[i].v].x;
        long long dy = coords[edges[i].u].y - coords[edges[i].v].y;
        d[i] = static_cast<long long>(round(sqrt(dx * dx + dy * dy)));
    }

    std::vector<DSU> future_connectivity(M + 1, DSU(N));
    for (int i = M - 1; i >= 0; --i) {
        future_connectivity[i] = future_connectivity[i + 1];
        future_connectivity[i].unite(edges[i].u, edges[i].v);
    }

    DSU dsu(N);
    int edges_count = 0;

    for (int i = 0; i < M; ++i) {
        long long l_i;
        std::cin >> l_i;

        int u_i = edges[i].u;
        int v_i = edges[i].v;

        int root_u = dsu.find(u_i);
        int root_v = dsu.find(v_i);

        if (root_u == root_v) {
            std::cout << 0 << std::endl;
        } else {
            if (future_connectivity[i + 1].find(u_i) != future_connectivity[i + 1].find(v_i)) {
                std::cout << 1 << std::endl;
                dsu.unite(u_i, v_i);
                edges_count++;
            } else {
                long long min_d_alt = -1;

                for (int j = i + 1; j < M; ++j) {
                    if ((dsu.find(edges[j].u) == root_u && dsu.find(edges[j].v) == root_v) ||
                        (dsu.find(edges[j].u) == root_v && dsu.find(edges[j].v) == root_u)) {
                        if (min_d_alt == -1 || d[j] < min_d_alt) {
                            min_d_alt = d[j];
                        }
                    }
                }

                bool take_edge = false;
                if (min_d_alt == -1) {
                    take_edge = true;
                } else {
                    int edges_needed = (N - 1) - edges_count;
                    int edges_remaining = M - i;
                    double rate = 0;
                    if (edges_remaining > 0) {
                        rate = static_cast<double>(edges_needed) / edges_remaining;
                    }
                    double factor = 1.5 + 2.0 * rate;

                    if (l_i < factor * min_d_alt) {
                        take_edge = true;
                    }
                }

                if (take_edge) {
                    std::cout << 1 << std::endl;
                    dsu.unite(u_i, v_i);
                    edges_count++;
                } else {
                    std::cout << 0 << std::endl;
                }
            }
        }
    }

    return 0;
}