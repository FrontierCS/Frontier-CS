#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0): n(n), p(n), sz(n,1) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a = find(a); b = find(b);
        if(a == b) return false;
        if(sz[a] < sz[b]) swap(a,b);
        p[b] = a;
        sz[a] += sz[b];
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    // Read coordinates
    for (int i = 0; i < N; ++i) {
        int x, y;
        if (!(cin >> x >> y)) return 0;
    }

    // Read edges
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
    }

    DSU dsu(N);

    // Online processing of edge lengths
    for (int i = 0; i < M; ++i) {
        int l;
        cin >> l; // length given but not used in this simple strategy
        bool take = dsu.unite(edges[i].first, edges[i].second);
        cout << (take ? 1 : 0) << '\n' << flush;
    }

    return 0;
}