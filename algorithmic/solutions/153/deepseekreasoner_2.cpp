#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <bitset>
using namespace std;

const int N = 400;
const int M = 1995;

struct Edge {
    int u, v;
    int d;
    int idx;
};

int parent[N], sz[N];

void dsu_init() {
    for (int i = 0; i < N; ++i) {
        parent[i] = i;
        sz[i] = 1;
    }
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
    if (sz[x] < sz[y]) swap(x, y);
    parent[y] = x;
    sz[x] += sz[y];
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i)
        cin >> x[i] >> y[i];

    vector<int> u(M), v(M), d(M);
    for (int i = 0; i < M; ++i) {
        cin >> u[i] >> v[i];
        double dx = x[u[i]] - x[v[i]];
        double dy = y[u[i]] - y[v[i]];
        d[i] = (int)round(sqrt(dx * dx + dy * dy));
    }

    // compute 5 edge-disjoint spanning trees
    vector<int> tree_id(M, -1);
    vector<bool> used(M, false);
    for (int t = 0; t < 5; ++t) {
        dsu_init();
        vector<Edge> edges_t;
        for (int i = 0; i < M; ++i) {
            if (!used[i])
                edges_t.push_back({u[i], v[i], d[i], i});
        }
        sort(edges_t.begin(), edges_t.end(),
             [](const Edge& a, const Edge& b) { return a.d < b.d; });
        for (const Edge& e : edges_t) {
            if (find(e.u) != find(e.v)) {
                unite(e.u, e.v);
                tree_id[e.idx] = t;
                used[e.idx] = true;
            }
        }
    }

    // adjacency list and edge index matrix
    vector<vector<pair<int, int>>> adj(N);
    vector<vector<int>> edge_id(N, vector<int>(N, -1));
    for (int i = 0; i < M; ++i) {
        int a = u[i], b = v[i];
        adj[a].emplace_back(b, i);
        adj[b].emplace_back(a, i);
        edge_id[a][b] = edge_id[b][a] = i;
    }

    // online phase
    dsu_init();
    vector<bitset<N>> comp_bits(N);
    for (int i = 0; i < N; ++i) {
        comp_bits[i].reset();
        comp_bits[i].set(i);
    }
    int adopted = 0;

    // base acceptance thresholds for each tree (lower for later trees)
    double base_th[5] = {2.0, 1.9, 1.8, 1.7, 1.6};

    for (int i = 0; i < M; ++i) {
        int l;
        cin >> l;
        if (adopted == N - 1) {
            cout << 0 << endl;
            continue;
        }
        int a = u[i], b = v[i];
        int ra = find(a), rb = find(b);
        if (ra == rb) {
            cout << 0 << endl;
            continue;
        }

        // count future edges that could connect the same two components
        int n_future = 0;
        int small_root = ra, large_root = rb;
        if (sz[ra] > sz[rb]) {
            small_root = rb;
            large_root = ra;
        }
        for (int vx = 0; vx < N; ++vx) {
            if (!comp_bits[small_root].test(vx)) continue;
            for (const auto& nb : adj[vx]) {
                int vy = nb.first;
                int eid = nb.second;
                if (eid > i && comp_bits[large_root].test(vy))
                    ++n_future;
            }
        }

        int needed = (N - 1) - adopted;
        int remaining = M - i - 1;
        double urgency = (double)needed / (remaining + 1e-9);
        double th = (tree_id[i] != -1) ? base_th[tree_id[i]] : 1.5;

        // adjust threshold by urgency
        double urgency_factor = min(1.0, urgency);
        th += (3.0 - th) * urgency_factor;

        // adjust by number of future alternatives
        double nf_factor = 0.0;
        if (n_future == 0)
            nf_factor = 1.0;
        else if (n_future < 5)
            nf_factor = (5.0 - n_future) / 5.0;
        th += (3.0 - th) * nf_factor;
        th = min(th, 3.0);

        double r = (double)l / d[i];
        bool adopt = (r <= th) || (urgency > 1.0);

        if (adopt) {
            cout << 1 << endl;
            if (sz[ra] < sz[rb]) swap(ra, rb);
            parent[rb] = ra;
            sz[ra] += sz[rb];
            comp_bits[ra] |= comp_bits[rb];
            ++adopted;
        } else {
            cout << 0 << endl;
        }
        cout.flush();
    }

    return 0;
}