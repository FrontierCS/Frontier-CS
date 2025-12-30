#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <cassert>

using namespace std;

const int N = 400;
const int M = 1995;

struct DSU {
    vector<int> parent, rank;
    DSU(int n) : parent(n), rank(n, 1) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] != x)
            parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        x = find(x);
        y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) swap(x, y);
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
        return true;
    }
};

// round Euclidean distance
int calc_dist(int x1, int y1, int x2, int y2) {
    double dx = x1 - x2;
    double dy = y1 - y2;
    return (int)round(sqrt(dx*dx + dy*dy));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }
    vector<int> u(M), v(M);
    for (int i = 0; i < M; i++) {
        cin >> u[i] >> v[i];
    }

    // compute all pairwise rounded distances
    vector<vector<int>> dist(N, vector<int>(N, 0));
    vector<tuple<int, int, int>> all_edges; // (d, u, v)
    for (int i = 0; i < N; i++) {
        for (int j = i+1; j < N; j++) {
            int d = calc_dist(x[i], y[i], x[j], y[j]);
            dist[i][j] = dist[j][i] = d;
            all_edges.emplace_back(d, i, j);
        }
    }
    // sort edges by distance, then by vertices for deterministic tie-breaking
    sort(all_edges.begin(), all_edges.end(),
         [](const auto& a, const auto& b) {
             if (get<0>(a) != get<0>(b)) return get<0>(a) < get<0>(b);
             if (get<1>(a) != get<1>(b)) return get<1>(a) < get<1>(b);
             return get<2>(a) < get<2>(b);
         });

    // assign each edge to one of the 5 MSTs (tree_id 1..5)
    vector<vector<int>> tree_id_map(N, vector<int>(N, 0));
    for (int t = 1; t <= 5; t++) {
        DSU dsu(N);
        int taken = 0;
        for (const auto& e : all_edges) {
            int d = get<0>(e);
            int a = get<1>(e);
            int b = get<2>(e);
            if (tree_id_map[a][b] != 0) continue; // already used in previous tree
            if (dsu.find(a) != dsu.find(b)) {
                dsu.unite(a, b);
                tree_id_map[a][b] = t;
                tree_id_map[b][a] = t;
                taken++;
                if (taken == N-1) break;
            }
        }
    }

    // for each given edge, store its d and tree_id
    vector<int> d_vals(M);
    vector<int> tree_ids(M);
    for (int i = 0; i < M; i++) {
        d_vals[i] = dist[u[i]][v[i]];
        tree_ids[i] = tree_id_map[u[i]][v[i]];
    }

    DSU dsu(N);
    int adopted = 0;

    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;
        if (dsu.find(u[i]) == dsu.find(v[i])) {
            cout << 0 << endl;
            continue;
        }
        int compA = dsu.find(u[i]);
        int compB = dsu.find(v[i]);

        // examine future edges that connect the same components
        int future_count = 0;
        int min_d_future = 1e9;
        for (int j = i+1; j < M; j++) {
            int c1 = dsu.find(u[j]);
            int c2 = dsu.find(v[j]);
            if ((c1 == compA && c2 == compB) || (c1 == compB && c2 == compA)) {
                future_count++;
                min_d_future = min(min_d_future, d_vals[j]);
            }
        }

        bool take = false;
        if (future_count == 0) {
            take = true;
        } else {
            int remaining_needed = (N-1) - adopted;
            int remaining_edges = M - i - 1;
            double pressure = (double)remaining_needed / remaining_edges;
            double threshold = 2.0 * min_d_future;
            if (pressure > 1.0) {
                threshold *= 1.5;
            } else if (pressure > 0.8) {
                threshold *= 1.2;
            } else if (pressure > 0.5) {
                threshold *= 1.0 + 0.3 * pressure;
            }
            // favour edges from the first two MSTs
            if (tree_ids[i] <= 2) {
                threshold *= 1.1;
            }
            if (l <= threshold) {
                take = true;
            } else if (l <= d_vals[i] * 1.5) { // very good deal
                take = true;
            }
        }

        if (take) {
            cout << 1 << endl;
            dsu.unite(u[i], v[i]);
            adopted++;
        } else {
            cout << 0 << endl;
        }
        cout.flush();
    }

    return 0;
}