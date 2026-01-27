#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0): n(n), p(n), sz(n,1) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a; sz[a]+=sz[b];
        return true;
    }
    bool same(int a,int b){ return find(a)==find(b); }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin>>x[i]>>y[i])) return 0;
    }
    struct Edge{int u,v,d;};
    vector<Edge> edges(M);
    for(int i=0;i<M;i++){
        int u,v;
        cin>>u>>v;
        edges[i].u=u; edges[i].v=v;
    }
    // compute d_i
    for(int i=0;i<M;i++){
        long long dx = x[edges[i].u]-x[edges[i].v];
        long long dy = y[edges[i].u]-y[edges[i].v];
        double dist = sqrt((double)dx*dx + (double)dy*dy);
        edges[i].d = (int)llround(dist);
    }

    // Build guarantee tree: MST on E with weight d
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if(edges[a].d != edges[b].d) return edges[a].d < edges[b].d;
        return a < b;
    });
    vector<char> in_tree(M, 0);
    DSU dsu_mst(N);
    int picked = 0;
    for(int idx : order){
        if(dsu_mst.unite(edges[idx].u, edges[idx].v)){
            in_tree[idx] = 1;
            picked++;
            if(picked==N-1) break;
        }
    }
    // Build LCA over guarantee tree (tree edges by d)
    vector<vector<pair<int,int>>> g(N);
    for(int i=0;i<M;i++){
        if(in_tree[i]){
            int u=edges[i].u, v=edges[i].v, w=edges[i].d;
            g[u].push_back({v,w});
            g[v].push_back({u,w});
        }
    }
    const int LOG = 10;
    vector<array<int,LOG>> up(N);
    vector<array<int,LOG>> mx(N);
    vector<int> depth(N, -1);
    int root = 0;
    // BFS/DFS to initialize
    {
        deque<int> dq;
        depth[root]=0;
        up[root][0]=root;
        mx[root][0]=0;
        dq.push_back(root);
        while(!dq.empty()){
            int u=dq.front(); dq.pop_front();
            for(auto [v,w]: g[u]){
                if(depth[v]!=-1) continue;
                depth[v]=depth[u]+1;
                up[v][0]=u;
                mx[v][0]=w;
                dq.push_back(v);
            }
        }
        // For any disconnected (shouldn't happen), but just in case
        for(int i=0;i<N;i++){
            if(depth[i]==-1){
                depth[i]=0;
                up[i][0]=i;
                mx[i][0]=0;
                dq.push_back(i);
                while(!dq.empty()){
                    int u2=dq.front(); dq.pop_front();
                    for(auto [v,w]: g[u2]){
                        if(depth[v]!=-1) continue;
                        depth[v]=depth[u2]+1;
                        up[v][0]=u2;
                        mx[v][0]=w;
                        dq.push_back(v);
                    }
                }
            }
        }
    }
    for(int k=1;k<LOG;k++){
        for(int v=0;v<N;v++){
            up[v][k] = up[ up[v][k-1] ][k-1];
            mx[v][k] = max(mx[v][k-1], mx[ up[v][k-1] ][k-1]);
        }
    }
    auto max_on_path = [&](int a, int b){
        if(a==b) return 0;
        int ans = 0;
        if(depth[a] < depth[b]) swap(a,b);
        int dd = depth[a] - depth[b];
        for(int k=LOG-1;k>=0;k--){
            if(dd & (1<<k)){
                ans = max(ans, mx[a][k]);
                a = up[a][k];
            }
        }
        if(a==b) return ans;
        for(int k=LOG-1;k>=0;k--){
            if(up[a][k] != up[b][k]){
                ans = max(ans, mx[a][k]);
                ans = max(ans, mx[b][k]);
                a = up[a][k];
                b = up[b][k];
            }
        }
        ans = max(ans, mx[a][0]);
        ans = max(ans, mx[b][0]);
        return ans;
    };

    // Parameters
    const double THR_DI = 1.22;    // accept if li <= THR_DI * di
    const double THR_PATH = 1.00;  // accept if li <= THR_PATH * max_d_on_Tg_path

    DSU dsu(N);

    for(int i=0;i<M;i++){
        int li;
        if(!(cin>>li)) return 0;
        int u = edges[i].u, v = edges[i].v;
        int di = edges[i].d;

        int ans = 0;
        if(!dsu.same(u,v)){
            if(in_tree[i]){
                ans = 1;
            }else{
                bool ok = false;
                // condition 1: cheap relative to its base distance
                if(li <= (int)floor(THR_DI * di + 1e-9)) ok = true;
                // condition 2: cheap relative to max base weight along path in guarantee tree
                int wmax = max_on_path(u, v);
                if(li <= (int)floor(THR_PATH * wmax + 1e-9)) ok = true;

                if(ok) ans = 1;
            }
            if(ans) dsu.unite(u,v);
        }else{
            ans = 0;
        }
        cout << ans << '\n' << flush;
    }

    return 0;
}