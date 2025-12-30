#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v, w, idx;
};

struct AdjEdge {
    int to;
    int idx;
    int w;
};

static inline long long isqrt_ll(long long x){
    if (x <= 0) return 0;
    long long r = (long long) sqrt((long double)x);
    while ((r+1) > 0 && (long long)(r+1)*(long long)(r+1) <= x) ++r;
    while ((long long)r*(long long)r > x) --r;
    return r;
}
static inline int ceil_sqrt_ll(long long x){
    if (x <= 0) return 0;
    long long r = isqrt_ll(x);
    if (r*r == x) return (int)r;
    return (int)(r+1);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, K;
    if(!(cin >> N >> M >> K)) {
        return 0;
    }
    vector<int> x(N+1), y(N+1);
    for(int i=1;i<=N;i++) cin >> x[i] >> y[i];
    vector<Edge> edges(M);
    vector<vector<AdjEdge>> g(N+1);
    for(int j=0;j<M;j++){
        int u,v,w; cin>>u>>v>>w;
        edges[j] = {u,v,w,j};
        g[u].push_back({v,j,w});
        g[v].push_back({u,j,w});
    }
    vector<int> a(K), b(K);
    for(int k=0;k<K;k++) cin >> a[k] >> b[k];

    // Precompute Dijkstra tree from node 1 (shortest path tree)
    const long long INF = (1LL<<60);
    vector<long long> dist(N+1, INF);
    vector<int> parent(N+1, -1);
    vector<int> pedge(N+1, -1);
    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
    dist[1] = 0;
    pq.push({0,1});
    while(!pq.empty()){
        auto [d,u] = pq.top(); pq.pop();
        if(d != dist[u]) continue;
        for(const auto &ae : g[u]){
            int v = ae.to;
            long long nd = d + ae.w;
            if(nd < dist[v]){
                dist[v] = nd;
                parent[v] = u;
                pedge[v] = ae.idx;
                pq.push({nd, v});
            }
        }
    }

    // Precompute candidate stations within 5000 for each resident
    const long long LIM2 = 5000LL * 5000LL;
    vector<vector<pair<int,long long>>> cand(K);
    cand.reserve(K);
    for(int kidx=0;kidx<K;kidx++){
        for(int i=1;i<=N;i++){
            long long dx = (long long)a[kidx] - x[i];
            long long dy = (long long)b[kidx] - y[i];
            long long d2 = dx*dx + dy*dy;
            if(d2 <= LIM2){
                cand[kidx].push_back({i, d2});
            }
        }
        if(cand[kidx].empty()){
            // Fallback: pick nearest anyway (won't be covered if >5000 but keeps assignment valid)
            long long bestd2 = (1LL<<62);
            int besti = 1;
            for(int i=1;i<=N;i++){
                long long dx = (long long)a[kidx] - x[i];
                long long dy = (long long)b[kidx] - y[i];
                long long d2 = dx*dx + dy*dy;
                if(d2 < bestd2){
                    bestd2 = d2; besti = i;
                }
            }
            cand[kidx].push_back({besti, bestd2});
        }
        sort(cand[kidx].begin(), cand[kidx].end(), [](const pair<int,long long>& A, const pair<int,long long>& B){
            if (A.second != B.second) return A.second < B.second;
            return A.first < B.first;
        });
    }

    // Order residents by decreasing minimal distance to any station (harder ones first)
    vector<int> order(K);
    iota(order.begin(), order.end(), 0);
    vector<long long> mind2(K, (1LL<<62));
    for(int kidx=0;kidx<K;kidx++){
        if(!cand[kidx].empty()){
            mind2[kidx] = cand[kidx][0].second;
        }
    }
    sort(order.begin(), order.end(), [&](int i, int j){
        if (mind2[i] != mind2[j]) return mind2[i] > mind2[j];
        return i < j;
    });

    // Greedy assignment minimizing sum of P_i^2 ignoring cable costs
    vector<long long> maxsq(N+1, -1);
    vector<int> assigned_station(K, -1);
    for(int idx=0; idx<K; idx++){
        int kidx = order[idx];
        long long bestDelta = (1LL<<62);
        int bestStation = cand[kidx][0].first;
        long long bestd2 = cand[kidx][0].second;
        for(auto &p : cand[kidx]){
            int st = p.first;
            long long d2 = p.second;
            long long curMax = maxsq[st];
            int oldr = (curMax < 0 ? 0 : ceil_sqrt_ll(curMax));
            long long oldP2 = 1LL * oldr * oldr;
            long long newMax = (curMax < 0 ? d2 : (curMax >= d2 ? curMax : d2));
            int newr = ceil_sqrt_ll(newMax);
            long long newP2 = 1LL * newr * newr;
            long long delta = newP2 - oldP2;
            if(delta < bestDelta || (delta == bestDelta && d2 < bestd2)){
                bestDelta = delta;
                bestStation = st;
                bestd2 = d2;
            }
        }
        assigned_station[kidx] = bestStation;
        if (maxsq[bestStation] < bestd2) maxsq[bestStation] = bestd2;
    }

    // Build B via union of shortest paths to all used stations
    vector<int> B(M, 0);
    vector<char> usedStation(N+1, 0);
    for(int i=1;i<=N;i++){
        if(maxsq[i] >= 0) usedStation[i] = 1;
    }
    for(int i=1;i<=N;i++){
        if(!usedStation[i]) continue;
        int cur = i;
        while(cur != 1 && pedge[cur] != -1){
            int eidx = pedge[cur];
            if(!B[eidx]) B[eidx] = 1;
            cur = parent[cur];
        }
    }

    // Compute P_i from maxsq
    vector<int> P(N+1, 0);
    for(int i=1;i<=N;i++){
        if(maxsq[i] < 0) P[i] = 0;
        else {
            int r = ceil_sqrt_ll(maxsq[i]);
            if(r > 5000) r = 5000; // clamp just in case
            P[i] = r;
        }
    }

    // Output
    for(int i=1;i<=N;i++){
        if(i > 1) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for(int j=0;j<M;j++){
        if(j > 0) cout << ' ';
        cout << B[j];
    }
    cout << '\n';
    return 0;
}