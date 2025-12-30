#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n_) : n(n_), p(n_), r(n_, 0) {
        iota(p.begin(), p.end(), 0);
    }
    int find(int x) {
        if (p[x] == x) return x;
        return p[x] = find(p[x]);
    }
    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) swap(a, b);
        p[b] = a;
        if (r[a] == r[b]) ++r[a];
        return true;
    }
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

    vector<int> u(M), v(M), d(M);
    for (int i = 0; i < M; ++i) {
        cin >> u[i] >> v[i];
        int dx = x[u[i]] - x[v[i]];
        int dy = y[u[i]] - y[v[i]];
        double dist = sqrt((double)dx * dx + (double)dy * dy);
        d[i] = (int)llround(dist);
    }

    struct Edge {
        int idx, u, v, d;
    };
    vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        edges[i] = {i, u[i], v[i], d[i]};
    }

    sort(edges.begin(), edges.end(), [](const Edge &a, const Edge &b) {
        return a.d < b.d;
    });

    DSU dsu(N);
    vector<char> in_mst(M, 0);
    int cnt = 0;
    for (auto &e : edges) {
        if (dsu.unite(e.u, e.v)) {
            in_mst[e.idx] = 1;
            if (++cnt == N - 1) break;
        }
    }

    for (int i = 0; i < M; ++i) {
        long long li;
        if (!(cin >> li)) return 0;
        int ans = in_mst[i] ? 1 : 0;
        cout << ans << '\n' << flush;
    }

    return 0;
}