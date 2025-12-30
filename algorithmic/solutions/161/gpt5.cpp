#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
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

static inline long long dist2_ll(long long x1, long long y1, long long x2, long long y2){
    long long dx = x1 - x2;
    long long dy = y1 - y2;
    return dx*dx + dy*dy;
}

static inline int ceil_sqrt_ll(long long x){
    if(x<=0) return 0;
    long double rt = sqrt((long double)x);
    long long s = (long long)rt;
    while(s*s < x) ++s;
    while((s-1)>=0 && (s-1)*(s-1) >= x) --s;
    return (int)s;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N,M,K;
    if(!(cin>>N>>M>>K)) return 0;
    vector<long long> x(N+1), y(N+1);
    for(int i=1;i<=N;i++){
        cin>>x[i]>>y[i];
    }
    struct Edge{int u,v; long long w; int id;};
    vector<Edge> edges;
    edges.reserve(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin>>u>>v>>w;
        edges.push_back({u,v,w,j});
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++){
        cin>>a[k]>>b[k];
    }

    // Build MST using Kruskal
    vector<Edge> sorted_edges = edges;
    sort(sorted_edges.begin(), sorted_edges.end(), [](const Edge& A, const Edge& B){
        if(A.w != B.w) return A.w < B.w;
        return A.id < B.id;
    });
    DSU dsu(N+1);
    vector<int> mst_edge_ids;
    mst_edge_ids.reserve(N-1);
    for(const auto &e: sorted_edges){
        if(dsu.unite(e.u, e.v)){
            mst_edge_ids.push_back(e.id);
            if((int)mst_edge_ids.size()==N-1) break;
        }
    }
    // Build adjacency for MST
    vector<vector<pair<int,int>>> adj(N+1);
    vector<char> inMST(M, 0);
    for(int id: mst_edge_ids) inMST[id]=1;
    for(const auto &e: edges){
        if(inMST[e.id]){
            adj[e.u].push_back({e.v, e.id});
            adj[e.v].push_back({e.u, e.id});
        }
    }
    // Assign residents to nearest vertex
    vector<vector<long long>> assigned_d2(N+1);
    vector<int> assign_idx(K, -1);
    for(int k=0;k<K;k++){
        long long best = LLONG_MAX;
        int besti = 1;
        for(int i=1;i<=N;i++){
            long long d2 = dist2_ll(x[i], y[i], a[k], b[k]);
            if(d2 < best){
                best = d2;
                besti = i;
            }
        }
        assign_idx[k] = besti;
        assigned_d2[besti].push_back(best);
    }
    vector<int> P(N+1, 0);
    vector<char> used(N+1, 0);
    used[1] = 1; // ensure root kept
    for(int i=1;i<=N;i++){
        if(!assigned_d2[i].empty()){
            long long mx = 0;
            for(auto d2: assigned_d2[i]) if(d2 > mx) mx = d2;
            int r = ceil_sqrt_ll(mx);
            if(r > 5000) r = 5000;
            P[i] = r;
            if(P[i] > 0) used[i] = 1;
        } else {
            P[i] = 0;
        }
    }
    // Prune leaves in MST not used (Steiner pruning)
    vector<int> deg(N+1,0);
    for(int i=1;i<=N;i++){
        deg[i] = (int)adj[i].size();
    }
    vector<char> keepEdge(M, 0);
    for(int id: mst_edge_ids) keepEdge[id]=1;
    deque<int> dq;
    for(int i=1;i<=N;i++){
        if(i!=1 && !used[i] && deg[i]==1){
            dq.push_back(i);
        }
    }
    while(!dq.empty()){
        int v = dq.front(); dq.pop_front();
        if(v==1) continue;
        if(used[v]) continue;
        if(deg[v]!=1) continue;
        // find the only kept neighbor edge
        int to = -1;
        int eid = -1;
        for(auto [nb, id]: adj[v]){
            if(keepEdge[id]){
                to = nb; eid = id; break;
            }
        }
        if(eid==-1) continue; // already removed
        keepEdge[eid] = 0;
        deg[v]--;
        deg[to]--;
        if(to!=1 && !used[to] && deg[to]==1){
            dq.push_back(to);
        }
    }

    // Output
    // P_1 ... P_N
    for(int i=1;i<=N;i++){
        if(i>1) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    // B_1 ... B_M
    for(int j=0;j<M;j++){
        if(j) cout << ' ';
        cout << (keepEdge[j]?1:0);
    }
    cout << '\n';
    return 0;
}