#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, rnk;
    DSU(int n=0): n(n), p(n+1), rnk(n+1,0) {
        for (int i=0;i<=n;i++) p[i]=i;
    }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(rnk[a]<rnk[b]) swap(a,b);
        p[b]=a;
        if(rnk[a]==rnk[b]) rnk[a]++;
        return true;
    }
};

int find_centroid(int n, const vector<vector<int>>& g) {
    vector<int> par(n+1,-1), sz(n+1,0), order;
    order.reserve(n);
    // iterative DFS to get postorder
    vector<pair<int,int>> st;
    st.reserve(2*n);
    st.push_back({1,0});
    par[1]=0;
    while(!st.empty()){
        auto [u, state] = st.back(); st.pop_back();
        if(state==0){
            st.push_back({u,1});
            for(int v: g[u]){
                if(v==par[u]) continue;
                par[v]=u;
                st.push_back({v,0});
            }
        }else{
            order.push_back(u);
        }
    }
    for(int u: order){
        sz[u]=1;
        for(int v: g[u]){
            if(v==par[u]) continue;
            sz[u]+=sz[v];
        }
    }
    int centroid = 1;
    int best = n+1;
    for(int u=1; u<=n; ++u){
        int maxPart = n - sz[u];
        for(int v: g[u]){
            if(v==par[u]) continue;
            maxPart = max(maxPart, sz[v]);
        }
        if(maxPart < best || (maxPart==best && u<centroid)){
            best = maxPart;
            centroid = u;
        }
    }
    return centroid;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tok;
    long long x;
    while (cin >> x) tok.push_back(x);
    if (tok.empty()) return 0;
    size_t idx = 0;
    long long n_ll = tok[idx++];
    if (n_ll <= 0) { cout << 1 << '\n'; return 0; }
    int n = (int)n_ll;
    long long rem = (long long)tok.size() - (long long)idx;
    vector<pair<int,int>> edges;
    auto try_parse_pairs = [&](size_t start_idx)->bool{
        if ((long long)tok.size() - (long long)start_idx < 2LL*(n-1)) return false;
        DSU dsu(n);
        int unions = 0;
        vector<pair<int,int>> e;
        e.reserve(n-1);
        for (int i=0;i<n-1;i++){
            long long u = tok[start_idx + 2LL*i];
            long long v = tok[start_idx + 2LL*i + 1];
            if (u < 1 || u > n || v < 1 || v > n || u == v) return false;
            e.emplace_back((int)u,(int)v);
            if (dsu.unite((int)u,(int)v)) unions++;
        }
        if (unions != n-1) return false;
        edges = move(e);
        return true;
    };
    auto try_parse_triples = [&](size_t start_idx)->bool{
        if ((long long)tok.size() - (long long)start_idx < 3LL*(n-1)) return false;
        DSU dsu(n);
        int unions = 0;
        vector<pair<int,int>> e;
        e.reserve(n-1);
        for (int i=0;i<n-1;i++){
            long long u = tok[start_idx + 3LL*i];
            long long v = tok[start_idx + 3LL*i + 1];
            // long long w = tok[start_idx + 3LL*i + 2]; // weight ignored
            if (u < 1 || u > n || v < 1 || v > n || u == v) return false;
            e.emplace_back((int)u,(int)v);
            if (dsu.unite((int)u,(int)v)) unions++;
        }
        if (unions != n-1) return false;
        edges = move(e);
        return true;
    };

    bool parsed = false;

    // Try exact fits first
    if (!parsed && rem == 2LL*(n-1)) parsed = try_parse_pairs(idx);
    if (!parsed && rem == 3LL*(n-1)) parsed = try_parse_triples(idx);

    // Try at least enough tokens
    if (!parsed && rem >= 2LL*(n-1)) parsed = try_parse_pairs(idx);
    if (!parsed && rem >= 3LL*(n-1)) parsed = try_parse_triples(idx);

    if (!parsed) {
        // Fallback: cannot parse edges; output a default valid node.
        cout << 1 << '\n';
        return 0;
    }

    vector<vector<int>> g(n+1);
    g.reserve(n+1);
    for (auto &e: edges){
        g[e.first].push_back(e.second);
        g[e.second].push_back(e.first);
    }

    int centroid = find_centroid(n, g);
    cout << centroid << '\n';
    return 0;
}