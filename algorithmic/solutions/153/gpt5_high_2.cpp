#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int a){ return p[a]==a ? a : p[a]=find(p[a]); }
    bool unite(int a, int b){
        a = find(a); b = find(b);
        if(a == b) return false;
        if(r[a] < r[b]) swap(a,b);
        p[b] = a;
        if(r[a] == r[b]) r[a]++;
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

    struct Edge { int u, v, d, idx; };
    vector<Edge> edges;
    edges.reserve(M);

    auto dist_round = [&](int u, int v)->int{
        long long dx = x[u] - x[v];
        long long dy = y[u] - y[v];
        long double d = sqrt((long double)dx*dx + (long double)dy*dy);
        return (int)llround(d);
    };

    vector<pair<int,int>> uv(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        uv[i] = {u, v};
    }
    for (int i = 0; i < M; ++i) {
        int u = uv[i].first, v = uv[i].second;
        int d = dist_round(u, v);
        edges.push_back({u, v, d, i});
    }

    // Kruskal on given graph using d as weight
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (edges[a].d != edges[b].d) return edges[a].d < edges[b].d;
        return edges[a].idx < edges[b].idx;
    });

    DSU dsu(N);
    vector<char> in_mst(M, 0);
    int taken = 0;
    for (int id : order) {
        if (dsu.unite(edges[id].u, edges[id].v)) {
            in_mst[edges[id].idx] = 1;
            if (++taken == N - 1) break;
        }
    }

    // Online phase: read lengths and decide
    for (int i = 0; i < M; ++i) {
        int li; 
        if (!(cin >> li)) li = 0; // safety
        int ans = in_mst[i] ? 1 : 0;
        cout << ans << '\n' << flush;
    }

    return 0;
}