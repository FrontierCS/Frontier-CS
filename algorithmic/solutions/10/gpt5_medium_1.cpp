#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n+1), r(n+1,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

struct Edge {
    int u, v;
    long long w;
    bool operator<(Edge const& other) const {
        if (w != other.w) return w < other.w;
        if (u != other.u) return u < other.u;
        return v < other.v;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        int n;
        if(!(cin >> n)) return 0;
        vector<Edge> edges;
        edges.reserve(1LL * n * (n - 1) / 2);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                long long d;
                cin >> d;
                if (j < i) {
                    edges.push_back({i+1, j+1, d});
                }
            }
        }
        sort(edges.begin(), edges.end());
        DSU dsu(n);
        int cnt = 0;
        for (auto &e : edges) {
            if (dsu.unite(e.u, e.v)) {
                cout << e.u << ' ' << e.v << ' ' << e.w << '\n';
                if (++cnt == n - 1) break;
            }
        }
        // If multiple test cases, separate outputs by nothing as per typical batch processing
    }
    return 0;
}