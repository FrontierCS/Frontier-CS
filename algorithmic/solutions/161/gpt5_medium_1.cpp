#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, r;
    DSU(int n=0){init(n);}
    void init(int n){p.resize(n); r.assign(n,0); iota(p.begin(), p.end(), 0);}
    int find(int x){ return p[x]==x? x : p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N,M,K;
    if(!(cin>>N>>M>>K)) return 0;
    vector<long long> x(N), y(N);
    for(int i=0;i<N;i++) cin>>x[i]>>y[i];
    struct Edge{int u,v; long long w; int idx;};
    vector<Edge> edges(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin>>u>>v>>w;
        --u;--v;
        edges[j]={u,v,w,j};
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++) cin>>a[k]>>b[k];

    // Assign each resident to nearest station and compute required P_i
    vector<int> P(N,0);
    for(int k=0;k<K;k++){
        int best = 0;
        long long bestd2 = (x[0]-a[k])*(x[0]-a[k]) + (y[0]-b[k])*(y[0]-b[k]);
        for(int i=1;i<N;i++){
            long long dx = x[i]-a[k];
            long long dy = y[i]-b[k];
            long long d2 = dx*dx + dy*dy;
            if(d2 < bestd2){
                bestd2 = d2;
                best = i;
            }
        }
        long long d2 = bestd2;
        long long s = (long long)floor(sqrt((long double)d2));
        while(s*s < d2) ++s;
        if(s > 5000) s = 5000; // safety clamp, though guaranteed unnecessary
        P[best] = max(P[best], (int)s);
    }

    // Build MST using Kruskal
    vector<Edge> e_sorted = edges;
    sort(e_sorted.begin(), e_sorted.end(), [](const Edge& a, const Edge& b){
        if(a.w != b.w) return a.w < b.w;
        return a.idx < b.idx;
    });
    DSU dsu(N);
    vector<vector<pair<int,int>>> adj(N); // neighbor, edge idx
    int cnt_added = 0;
    for(auto &e : e_sorted){
        if(dsu.unite(e.u, e.v)){
            adj[e.u].push_back({e.v, e.idx});
            adj[e.v].push_back({e.u, e.idx});
            cnt_added++;
            if(cnt_added == N-1) break;
        }
    }

    // Determine terminals (stations with P_i > 0)
    vector<int> isTerm(N, 0);
    for(int i=0;i<N;i++) if(P[i]>0) isTerm[i]=1;

    // On MST, include edges on paths from 1 to any terminal
    vector<int> B(M,0);
    function<int(int,int)> dfs = [&](int u, int p)->int{
        int cnt = isTerm[u] ? 1 : 0;
        for(auto [v, ei] : adj[u]){
            if(v==p) continue;
            int c = dfs(v, u);
            if(c > 0){
                B[ei] = 1;
                cnt += c;
            }
        }
        return cnt;
    };
    dfs(0, -1);

    // Output
    for(int i=0;i<N;i++){
        if(i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for(int j=0;j<M;j++){
        if(j) cout << ' ';
        cout << B[j];
    }
    cout << '\n';
    return 0;
}