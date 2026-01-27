#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, sz;
    DSU(int n=0){init(n);}
    void init(int n){p.resize(n+1); sz.assign(n+1,1); iota(p.begin(), p.end(), 0);}
    int find(int a){ while(p[a]!=a){ p[a]=p[p[a]]; a=p[a]; } return a; }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a; sz[a]+=sz[b];
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N,M,K;
    if(!(cin>>N>>M>>K)) return 0;
    vector<long long> x(N+1), y(N+1);
    for(int i=1;i<=N;i++){
        cin>>x[i]>>y[i];
    }
    struct Edge{int u,v; long long w;};
    vector<Edge> edges(M+1);
    for(int j=1;j<=M;j++){
        int u,v; long long w;
        cin>>u>>v>>w;
        edges[j]={u,v,w};
    }
    vector<long long> a(K+1), b(K+1);
    for(int k=1;k<=K;k++){
        cin>>a[k]>>b[k];
    }

    // Assign residents to nearest station
    vector<int> assign_to(K+1, 1);
    vector<vector<long long>> dist2_assigned(N+1); // store squared distances for assigned residents per station
    for(int k=1;k<=K;k++){
        long long best = (1LL<<62);
        int besti = 1;
        for(int i=1;i<=N;i++){
            long long dx = a[k]-x[i];
            long long dy = b[k]-y[i];
            long long d2 = dx*dx + dy*dy;
            if(d2 < best){
                best = d2;
                besti = i;
            }
        }
        assign_to[k] = besti;
        dist2_assigned[besti].push_back(best);
    }
    auto isqrt_ceil = [&](long long v)->int{
        long long r = sqrtl((long double)v);
        while(r*r < v) ++r;
        while((r-1)>=0 && (r-1)*(r-1) >= v) --r;
        return (int)r;
    };
    vector<int> P(N+1,0);
    for(int i=1;i<=N;i++){
        int rad = 0;
        for(long long d2 : dist2_assigned[i]){
            int r = isqrt_ceil(d2);
            if(r > rad) rad = r;
        }
        if(rad > 5000) rad = 5000;
        P[i] = rad;
    }

    // Build MST over all nodes
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 1);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        return edges[a].w < edges[b].w;
    });
    DSU dsu(N);
    vector<char> sel(M+1, 0);
    int cnt = 0;
    for(int id : idx){
        if(dsu.unite(edges[id].u, edges[id].v)){
            sel[id] = 1;
            cnt++;
            if(cnt == N-1) break;
        }
    }

    // Build adjacency from selected edges
    vector<vector<pair<int,int>>> adj(N+1);
    vector<int> deg(N+1,0);
    for(int j=1;j<=M;j++){
        if(sel[j]){
            int u=edges[j].u, v=edges[j].v;
            adj[u].push_back({v,j});
            adj[v].push_back({u,j});
            deg[u]++; deg[v]++;
        }
    }

    // Prune non-terminal leaves (terminals: P_i > 0 and node 1)
    queue<int> q;
    for(int i=1;i<=N;i++){
        if(i!=1 && P[i]==0 && deg[i]==1) q.push(i);
    }
    while(!q.empty()){
        int u = q.front(); q.pop();
        if(u==1) continue;
        if(P[u]>0) continue;
        if(deg[u]!=1) continue;
        // find the only selected edge
        int eidx = -1, v = -1;
        for(auto [to, eid] : adj[u]){
            if(sel[eid]){
                eidx = eid;
                v = to;
                break;
            }
        }
        if(eidx==-1) continue;
        sel[eidx] = 0;
        deg[u]--;
        deg[v]--;
        if(v!=1 && P[v]==0 && deg[v]==1){
            q.push(v);
        }
    }

    // Output
    for(int i=1;i<=N;i++){
        if(i>1) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for(int j=1;j<=M;j++){
        if(j>1) cout << ' ';
        cout << (sel[j]?1:0);
    }
    cout << '\n';
    return 0;
}