#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, sz;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x) {
        return p[x] == x ? x : p[x] = find(p[x]);
    }
    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        if (sz[a] < sz[b]) swap(a, b);
        p[b] = a;
        sz[a] += sz[b];
        return true;
    }
};

struct Edge {
    int u, v, idx;
    int d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        if (!(cin >> x[i] >> y[i])) return 0;
    }

    vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i].u = u;
        edges[i].v = v;
        edges[i].idx = i;
        long long dx = x[u] - x[v];
        long long dy = y[u] - y[v];
        double dist = sqrt((double)dx * dx + (double)dy * dy);
        int d = (int)llround(dist);
        edges[i].d = d;
    }

    // Compute MST with respect to d_i
    vector<Edge> sorted_edges = edges;
    sort(sorted_edges.begin(), sorted_edges.end(),
         [](const Edge &a, const Edge &b) { return a.d < b.d; });

    DSU uf(N);
    vector<char> inMST(M, false);
    for (const auto &e : sorted_edges) {
        if (uf.unite(e.u, e.v)) {
            inMST[e.idx] = true;
        }
    }

    // Online phase: decide for each edge
    for (int i = 0; i < M; ++i) {
        long long li;
        if (!(cin >> li)) return 0;
        int ans = inMST[i] ? 1 : 0;
        cout << ans << '\n' << flush;
    }

    return 0;
}