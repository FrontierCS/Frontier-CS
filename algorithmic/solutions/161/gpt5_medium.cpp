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

long long isqrt_floor(long long x){
    long double d = sqrt((long double)x);
    long long r = (long long)d;
    while ((r+1)*(long double)(r+1) <= (long double)x) r++;
    while ((long double)r*(long double)r > (long double)x) r--;
    return r;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, K;
    if(!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N), y(N);
    for(int i=0;i<N;i++) cin >> x[i] >> y[i];
    struct Edge { int u,v; long long w; int idx; };
    vector<Edge> edges(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin >> u >> v >> w;
        --u; --v;
        edges[j] = {u,v,w,j};
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++) cin >> a[k] >> b[k];

    // Kruskal MST
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j){
        if(edges[i].w != edges[j].w) return edges[i].w < edges[j].w;
        return i < j;
    });
    DSU dsu(N);
    vector<int> in_mst(M, 0);
    int cnt = 0;
    for(int id: ord){
        if(dsu.unite(edges[id].u, edges[id].v)){
            in_mst[id] = 1;
            cnt++;
            if(cnt == N-1) break;
        }
    }
    // Build MST adjacency
    vector<vector<pair<int,int>>> g(N);
    for(int j=0;j<M;j++){
        if(in_mst[j]){
            int u = edges[j].u, v = edges[j].v;
            g[u].push_back({v, j});
            g[v].push_back({u, j});
        }
    }
    // Parent arrays from root 0
    vector<int> parent(N, -1), parent_e(N, -1);
    queue<int> q;
    parent[0] = 0;
    q.push(0);
    while(!q.empty()){
        int u = q.front(); q.pop();
        for(auto [v, ei]: g[u]){
            if(parent[v] == -1){
                parent[v] = u;
                parent_e[v] = ei;
                q.push(v);
            }
        }
    }

    // Assign residents to nearest station
    vector<int> P(N, 0);
    for(int k=0;k<K;k++){
        int best_i = 0;
        long long best_d2 = (x[0]-a[k])*(x[0]-a[k]) + (y[0]-b[k])*(y[0]-b[k]);
        for(int i=1;i<N;i++){
            long long dx = x[i]-a[k];
            long long dy = y[i]-b[k];
            long long d2 = dx*dx + dy*dy;
            if(d2 < best_d2){
                best_d2 = d2;
                best_i = i;
            }
        }
        long long r = isqrt_floor(best_d2);
        long long rc = (r*r == best_d2) ? r : r+1;
        if(rc > 5000) rc = 5000; // safety
        if(P[best_i] < (int)rc) P[best_i] = (int)rc;
    }

    // Determine edges to turn on: union of paths in MST from 1 to all used vertices
    vector<int> B(M, 0);
    for(int i=0;i<N;i++){
        if(P[i] > 0){
            int v = i;
            while(v != 0){
                int ei = parent_e[v];
                if(ei == -1) break;
                B[ei] = 1;
                v = parent[v];
            }
        }
    }

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