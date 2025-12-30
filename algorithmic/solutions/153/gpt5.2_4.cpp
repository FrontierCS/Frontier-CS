#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    int comps;
    DSU(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
        comps = n;
    }
    int find(int a){ return p[a]==a ? a : p[a]=find(p[a]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a;
        sz[a]+=sz[b];
        comps--;
        return true;
    }
};

static inline int roundDist(int x1,int y1,int x2,int y2){
    long long dx = x1 - x2;
    long long dy = y1 - y2;
    double dist = sqrt((double)dx*dx + (double)dy*dy);
    return (int)llround(dist);
}

struct Edge {
    int u, v;
    int d;
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    constexpr int N = 400;
    constexpr int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin >> x[i] >> y[i])) return 0;
    }

    vector<Edge> edges(M);
    for(int i=0;i<M;i++){
        int u,v;
        cin >> u >> v;
        edges[i].u = u;
        edges[i].v = v;
        edges[i].d = roundDist(x[u], y[u], x[v], y[v]);
        if(edges[i].d < 1) edges[i].d = 1;
    }

    // Build proxy MST on given edges using d
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int a, int b){
        if(edges[a].d != edges[b].d) return edges[a].d < edges[b].d;
        if(edges[a].u != edges[b].u) return edges[a].u < edges[b].u;
        return edges[a].v < edges[b].v;
    });

    vector<char> inTree(M, 0);
    vector<vector<pair<int,int>>> treeAdj(N);
    DSU dsuBuild(N);
    int added = 0;
    for(int idx : ord){
        if(dsuBuild.unite(edges[idx].u, edges[idx].v)){
            inTree[idx] = 1;
            treeAdj[edges[idx].u].push_back({edges[idx].v, edges[idx].d});
            treeAdj[edges[idx].v].push_back({edges[idx].u, edges[idx].d});
            if(++added == N-1) break;
        }
    }

    // LCA with max edge on path in proxy tree
    int LOG = 1;
    while((1<<LOG) <= N) LOG++;
    vector<int> depth(N, 0);
    vector<vector<int>> up(LOG, vector<int>(N, 0));
    vector<vector<int>> mx(LOG, vector<int>(N, 0));

    // BFS/DFS from 0 (tree is connected)
    vector<int> st;
    st.reserve(N);
    st.push_back(0);
    up[0][0] = 0;
    mx[0][0] = 0;
    depth[0] = 0;
    vector<char> vis(N, 0);
    vis[0] = 1;
    for(size_t it=0; it<st.size(); it++){
        int v = st[it];
        for(auto [to,w] : treeAdj[v]){
            if(vis[to]) continue;
            vis[to] = 1;
            depth[to] = depth[v] + 1;
            up[0][to] = v;
            mx[0][to] = w;
            st.push_back(to);
        }
    }
    for(int k=1;k<LOG;k++){
        for(int v=0;v<N;v++){
            up[k][v] = up[k-1][ up[k-1][v] ];
            mx[k][v] = max(mx[k-1][v], mx[k-1][ up[k-1][v] ]);
        }
    }

    auto queryMax = [&](int a, int b)->int{
        if(a==b) return 0;
        int res = 0;
        if(depth[a] < depth[b]) swap(a,b);
        int diff = depth[a] - depth[b];
        for(int k=LOG-1;k>=0;k--){
            if(diff&(1<<k)){
                res = max(res, mx[k][a]);
                a = up[k][a];
            }
        }
        if(a==b) return res;
        for(int k=LOG-1;k>=0;k--){
            if(up[k][a] != up[k][b]){
                res = max(res, mx[k][a]);
                res = max(res, mx[k][b]);
                a = up[k][a];
                b = up[k][b];
            }
        }
        res = max(res, mx[0][a]);
        res = max(res, mx[0][b]);
        return res;
    };

    DSU dsuOnline(N);

    for(int i=0;i<M;i++){
        int l;
        if(!(cin >> l)) return 0;

        int ans = 0;
        if(dsuOnline.comps == 1){
            ans = 0;
        } else {
            int u = edges[i].u, v = edges[i].v;
            if(dsuOnline.find(u) == dsuOnline.find(v)){
                ans = 0;
            } else if(inTree[i]) {
                ans = 1;
                dsuOnline.unite(u,v);
            } else {
                int d = edges[i].d;
                int pathMx = queryMax(u,v);
                // Heuristic:
                // - accept very "lucky" edges (low l relative to d)
                // - or accept if it can plausibly replace a much heavier proxy-tree edge on the path
                bool ok1 = (long long)l * 10 <= (long long)d * 12; // l <= 1.2 d
                bool ok2 = ((long long)pathMx * 10 >= (long long)d * 13) && ((long long)l * 10 <= (long long)pathMx * 17); // pathMx>=1.3d && l<=1.7*pathMx
                if(ok1 || ok2){
                    ans = 1;
                    dsuOnline.unite(u,v);
                } else {
                    ans = 0;
                }
            }
        }

        cout << ans << '\n' << flush;
    }

    return 0;
}