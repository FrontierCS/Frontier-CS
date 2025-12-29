#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

static inline long long isqrt_floor_ll(long long x){
    long long r = sqrtl((long double)x);
    while((r+1)*(long long)(r+1) <= x) r++;
    while(r*r > x) r--;
    return r;
}
static inline int ceil_sqrt_ll(long long x){
    long long r = isqrt_floor_ll(x);
    if(r*r == x) return (int)r;
    return (int)(r+1);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, K;
    if(!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N+1), y(N+1);
    for(int i=1;i<=N;i++) cin >> x[i] >> y[i];
    struct Edge { int u,v; long long w; int idx; };
    vector<Edge> edges;
    edges.reserve(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin >> u >> v >> w;
        edges.push_back({u,v,w,j});
    }
    vector<long long> ax(K), by(K);
    for(int k=0;k<K;k++){
        cin >> ax[k] >> by[k];
    }

    const long long LIM2 = 5000LL*5000LL;

    // Precompute candidate stations within 5000 for each resident and minimal required radius
    vector<vector<pair<int,int>>> cand(K); // (station, reqR)
    vector<int> minReq(K, 5001);
    for(int k=0;k<K;k++){
        for(int i=1;i<=N;i++){
            long long dx = x[i]-ax[k];
            long long dy = y[i]-by[k];
            long long s = dx*dx + dy*dy;
            if(s <= LIM2){
                int req = ceil_sqrt_ll(s);
                cand[k].push_back({i, req});
                if(req < minReq[k]) minReq[k] = req;
            }
        }
        if(cand[k].empty()){
            // Fallback (shouldn't happen due to guarantees). Choose nearest station even if >5000.
            long long bestS = (1LL<<60); int bestI = 1;
            for(int i=1;i<=N;i++){
                long long dx = x[i]-ax[k];
                long long dy = y[i]-by[k];
                long long s = dx*dx + dy*dy;
                if(s < bestS){ bestS = s; bestI = i; }
            }
            int req = ceil_sqrt_ll(bestS);
            cand[k].push_back({bestI, min(req, 5000)});
            minReq[k] = min(req, 5000);
        }
    }

    // Order residents by harder first (descending minReq)
    vector<int> ord(K);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if(minReq[a] != minReq[b]) return minReq[a] > minReq[b];
        return a < b;
    });

    // Assign residents greedily minimizing incremental P_i^2
    vector<int> P(N+1, 0);
    for(int idx=0; idx<K; idx++){
        int k = ord[idx];
        long long bestCost = (1LL<<62);
        int bestI = -1, bestReq = 0;
        for(auto &pr : cand[k]){
            int i = pr.first;
            int req = pr.second;
            if(req > 5000) continue;
            long long cur = 1LL*P[i]*P[i];
            long long req2 = 1LL*req*req;
            long long cost = (req > P[i]) ? (req2 - cur) : 0;
            if(cost < bestCost || (cost==bestCost && (req < bestReq || (req==bestReq && i < bestI)))){
                bestCost = cost;
                bestI = i;
                bestReq = req;
            }
        }
        if(bestI==-1){
            // fallback: choose minimal req among cand
            int i = cand[k][0].first;
            int req = min(cand[k][0].second, 5000);
            bestI = i; bestReq = req;
        }
        if(bestReq > P[bestI]) P[bestI] = bestReq;
    }

    // Build adjacency (all edges)
    struct Adj { int to; int idx; long long w; };
    vector<vector<Adj>> graph(N+1);
    for(auto &e: edges){
        graph[e.u].push_back({e.v, e.idx, e.w});
        graph[e.v].push_back({e.u, e.idx, e.w});
    }

    // Build MST over all nodes (by weights)
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){ return edges[a].w < edges[b].w; });
    DSU dsu_all(N+1);
    vector<char> keepMST(M, false);
    vector<vector<pair<int,int>>> adjM(N+1);
    int cnt=0;
    for(int id: order){
        int u=edges[id].u, v=edges[id].v;
        if(dsu_all.unite(u,v)){
            keepMST[id]=true;
            adjM[u].push_back({v,id});
            adjM[v].push_back({u,id});
            cnt++;
            if(cnt==N-1) break;
        }
    }
    // Prune leaves that are not used (P[i]==0), keep node 1
    vector<int> deg(N+1,0);
    for(int i=1;i<=N;i++) deg[i]=(int)adjM[i].size();
    vector<char> used(N+1,false);
    used[1]=true;
    for(int i=1;i<=N;i++) if(P[i]>0) used[i]=true;
    queue<int> q;
    for(int i=1;i<=N;i++){
        if(!used[i] && deg[i]==1) q.push(i);
    }
    while(!q.empty()){
        int u=q.front(); q.pop();
        if(used[u] || deg[u]!=1) continue;
        for(auto &pr: adjM[u]){
            int v=pr.first, eid=pr.second;
            if(keepMST[eid]){
                keepMST[eid]=false;
                deg[u]--;
                deg[v]--;
                if(!used[v] && deg[v]==1) q.push(v);
                break;
            }
        }
    }
    long long sumMST = 0;
    for(int j=0;j<M;j++) if(keepMST[j]) sumMST += edges[j].w;

    // Alternative: connect only terminals via union of shortest paths between MST on terminal metric
    vector<int> terminals;
    terminals.push_back(1);
    for(int i=2;i<=N;i++) if(P[i]>0) terminals.push_back(i);
    int T = (int)terminals.size();

    vector<char> keepPaths(M, false);
    long long sumPaths = (1LL<<62);

    if(T<=1){
        // No edges needed
        sumPaths = 0;
    }else{
        // Compute pairwise distances between terminals using Dijkstra
        const long long INF = (1LL<<60);
        vector<vector<long long>> distT(T, vector<long long>(T, INF));
        for(int si=0; si<T; si++){
            int s = terminals[si];
            vector<long long> dist(N+1, INF);
            priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
            dist[s]=0;
            pq.push({0,s});
            while(!pq.empty()){
                auto [d,u]=pq.top(); pq.pop();
                if(d!=dist[u]) continue;
                for(auto &ad: graph[u]){
                    long long nd = d + ad.w;
                    if(nd < dist[ad.to]){
                        dist[ad.to] = nd;
                        pq.push({nd, ad.to});
                    }
                }
            }
            for(int tj=0; tj<T; tj++){
                distT[si][tj] = dist[terminals[tj]];
            }
        }

        // Build MST on terminals complete graph
        struct TEdge { int a,b; long long w; };
        vector<TEdge> termEdges;
        termEdges.reserve(T*(T-1)/2);
        for(int i=0;i<T;i++){
            for(int j=i+1;j<T;j++){
                termEdges.push_back({i,j,distT[i][j]});
            }
        }
        sort(termEdges.begin(), termEdges.end(), [](const TEdge& A, const TEdge& B){ return A.w < B.w; });
        DSU dsuT(T);
        vector<pair<int,int>> mstPairs;
        for(auto &te: termEdges){
            if(dsuT.unite(te.a, te.b)){
                mstPairs.push_back({te.a, te.b});
                if((int)mstPairs.size() == T-1) break;
            }
        }

        // Reconstruct union of shortest paths for each pair
        vector<char> keepTemp(M, false);
        auto add_path = [&](int sIdx, int tIdx){
            int s = terminals[sIdx];
            int t = terminals[tIdx];
            const long long INF2 = (1LL<<60);
            vector<long long> dist(N+1, INF2);
            vector<int> prevEdge(N+1, -1);
            vector<int> prevV(N+1, -1);
            priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
            dist[s]=0;
            pq.push({0,s});
            while(!pq.empty()){
                auto [d,u] = pq.top(); pq.pop();
                if(d!=dist[u]) continue;
                if(u==t) break;
                for(auto &ad: graph[u]){
                    long long nd = d + ad.w;
                    if(nd < dist[ad.to]){
                        dist[ad.to] = nd;
                        prevEdge[ad.to] = ad.idx;
                        prevV[ad.to] = u;
                        pq.push({nd, ad.to});
                    }
                }
            }
            int cur = t;
            while(cur != s && prevEdge[cur] != -1){
                int eidx = prevEdge[cur];
                keepTemp[eidx] = true;
                cur = prevV[cur];
            }
        };

        for(auto &pr: mstPairs){
            add_path(pr.first, pr.second);
        }
        long long sumK = 0;
        for(int j=0;j<M;j++) if(keepTemp[j]) sumK += edges[j].w;
        keepPaths = move(keepTemp);
        sumPaths = sumK;
    }

    // Choose the better of pruned MST and shortest path union
    vector<char> keepFinal(M, false);
    if(sumPaths < sumMST){
        keepFinal = keepPaths;
    }else{
        keepFinal = keepMST;
    }

    // Output
    for(int i=1;i<=N;i++){
        if(i>1) cout << ' ';
        int val = P[i];
        if(val < 0) val = 0;
        if(val > 5000) val = 5000;
        cout << val;
    }
    cout << '\n';
    for(int j=0;j<M;j++){
        if(j) cout << ' ';
        cout << (keepFinal[j] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}