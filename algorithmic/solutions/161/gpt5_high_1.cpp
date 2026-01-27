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

long long ceil_sqrt_ll(long long x){
    if(x<=0) return 0;
    long long s = (long long)floor(sqrtl((long double)x));
    while(s*s < x) ++s;
    while((s-1)>=0 && (s-1)*(s-1) >= x) --s;
    return s;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, K;
    if(!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N), y(N);
    for(int i=0;i<N;i++) cin >> x[i] >> y[i];
    vector<int> eu(M), ev(M);
    vector<long long> ew(M);
    vector<vector<pair<int,int>>> adj(N);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin >> u >> v >> w;
        --u; --v;
        eu[j]=u; ev[j]=v; ew[j]=w;
        adj[u].push_back({v,j});
        adj[v].push_back({u,j});
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++) cin >> a[k] >> b[k];

    // Assign each resident to nearest vertex
    vector<long long> maxd2(N, -1);
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
        if(maxd2[best_i] < best_d2) maxd2[best_i] = best_d2;
    }

    // Compute P_i
    vector<int> P(N,0);
    vector<int> terminals;
    for(int i=0;i<N;i++){
        if(maxd2[i] >= 0){
            long long s = ceil_sqrt_ll(maxd2[i]);
            if(s > 5000) s = 5000;
            P[i] = (int)s;
            if(P[i] > 0) terminals.push_back(i);
        }
    }
    // Ensure root (0) is included as a terminal for connectivity
    bool has_root = false;
    for(int v: terminals) if(v==0){ has_root = true; break; }
    if(!has_root) terminals.push_back(0);

    // Build mapping from vertex to terminal index
    int T = (int)terminals.size();
    vector<int> termIndex(N, -1);
    for(int i=0;i<T;i++) termIndex[terminals[i]] = i;

    // Dijkstra from each terminal
    const long long INF = (long long)4e18;
    vector<vector<long long>> distAll(T, vector<long long>(N, INF));
    vector<vector<int>> prevEdgeAll(T, vector<int>(N, -1));
    for(int ti=0; ti<T; ti++){
        int s = terminals[ti];
        auto &dist = distAll[ti];
        auto &prevE = prevEdgeAll[ti];
        priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
        dist[s] = 0;
        pq.push({0, s});
        while(!pq.empty()){
            auto [d,u] = pq.top(); pq.pop();
            if(d != dist[u]) continue;
            for(auto [v,eid]: adj[u]){
                long long nd = d + ew[eid];
                if(nd < dist[v]){
                    dist[v] = nd;
                    prevE[v] = eid;
                    pq.push({nd, v});
                }
            }
        }
    }

    // Build complete graph distances between terminals
    vector<vector<long long>> dMat(T, vector<long long>(T, INF));
    for(int i=0;i<T;i++){
        for(int j=0;j<T;j++){
            dMat[i][j] = distAll[i][terminals[j]];
        }
    }

    // Prim's algorithm on terminals with distances dMat, root at vertex 0
    int rootIdx = termIndex[0];
    if(rootIdx == -1){
        // shouldn't happen as we ensured root included
        rootIdx = 0;
    }
    vector<char> inMST(T, false);
    vector<long long> minCost(T, INF);
    vector<int> parent(T, -1);
    minCost[rootIdx] = 0;

    vector<int> edgeOn(M, 0);

    for(int it=0; it<T; it++){
        int u = -1;
        long long best = INF;
        for(int i=0;i<T;i++){
            if(!inMST[i] && minCost[i] < best){
                best = minCost[i];
                u = i;
            }
        }
        if(u == -1) break;
        inMST[u] = true;
        if(parent[u] != -1){
            int p = parent[u];
            int src = terminals[p];
            int dst = terminals[u];
            // Reconstruct path from src to dst using prevEdgeAll[p]
            int cur = dst;
            auto &prevE = prevEdgeAll[p];
            while(cur != src){
                int eid = prevE[cur];
                if(eid < 0) break; // safety
                edgeOn[eid] = 1;
                int a1 = eu[eid], b1 = ev[eid];
                cur = a1 ^ b1 ^ cur;
            }
        }
        for(int v=0; v<T; v++){
            if(!inMST[v]){
                long long w = dMat[u][v];
                if(w < minCost[v]){
                    minCost[v] = w;
                    parent[v] = u;
                }
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
        cout << (edgeOn[j] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}