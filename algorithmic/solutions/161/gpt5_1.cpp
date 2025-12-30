#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    long long w;
};

static inline int floor_isqrtll(long long x){
    long long r = sqrtl((long double)x);
    while((r+1)*(r+1) <= x) ++r;
    while(r*r > x) --r;
    return (int)r;
}
static inline int ceil_isqrtll(long long x){
    int r = floor_isqrtll(x);
    if(1LL*r*r == x) return r;
    return r+1;
}

struct Graph {
    int N, M;
    vector<Edge> edges;
    vector<vector<pair<int,int>>> adj; // node -> list of (to, edge index)
    Graph(int n=0, int m=0):N(n),M(m),edges(m+1),adj(n+1){}
    void add_edge(int idx, int u, int v, long long w){
        edges[idx] = {u,v,w};
        adj[u].push_back({v, idx});
        adj[v].push_back({u, idx});
    }
};

struct DijkstraRes {
    vector<long long> dist;
    vector<int> parentEdge; // edge index used to reach node
};

DijkstraRes dijkstra_from(const Graph &g, int s){
    const long long INF = (1LL<<62);
    int n = g.N;
    vector<long long> dist(n+1, INF);
    vector<int> parentEdge(n+1, -1);
    using P = pair<long long,int>;
    priority_queue<P, vector<P>, greater<P>> pq;
    dist[s] = 0;
    pq.push({0, s});
    while(!pq.empty()){
        auto [d,u] = pq.top(); pq.pop();
        if(d!=dist[u]) continue;
        for(auto [v, ei]: g.adj[u]){
            long long nd = d + g.edges[ei].w;
            if(nd < dist[v]){
                dist[v] = nd;
                parentEdge[v] = ei;
                pq.push({nd, v});
            }
        }
    }
    return {move(dist), move(parentEdge)};
}

// Connect terminals by building MST on metric closure (shortest path distances),
// then union shortest paths to get actual edges to turn on.
pair<vector<char>, long long> connect_terminals_metric_MST(const Graph &g, const vector<int> &terms){
    int T = (int)terms.size();
    if(T == 0){
        vector<char> B(g.M+1, 0);
        return {B, 0LL};
    }
    // Run Dijkstra from each terminal
    vector<DijkstraRes> dj(T);
    for(int i=0;i<T;i++){
        dj[i] = dijkstra_from(g, terms[i]);
    }
    // Build distance matrix between terminals
    const long long INF = (1LL<<62);
    vector<vector<long long>> distT(T, vector<long long>(T, INF));
    for(int i=0;i<T;i++){
        for(int j=0;j<T;j++){
            distT[i][j] = dj[i].dist[terms[j]];
        }
    }
    // Prim's MST on the complete graph of terminals
    vector<int> parent(T, -1);
    vector<long long> key(T, INF);
    vector<char> inMST(T, 0);
    key[0] = 0;
    for(int it=0; it<T; it++){
        int u = -1;
        long long best = INF;
        for(int i=0;i<T;i++){
            if(!inMST[i] && key[i] < best){
                best = key[i];
                u = i;
            }
        }
        if(u == -1) break;
        inMST[u] = 1;
        for(int v=0; v<T; v++){
            if(!inMST[v] && distT[u][v] < key[v]){
                key[v] = distT[u][v];
                parent[v] = u;
            }
        }
    }
    // Union shortest paths of MST edges
    vector<char> B(g.M+1, 0);
    long long sumW = 0;
    for(int v=1; v<T; v++){
        int u = parent[v];
        if(u < 0) continue;
        int srcIdx = u;
        int tgtNode = terms[v];
        // Reconstruct path from src (terms[u]) to target (terms[v]) using parentEdge from dj[srcIdx]
        int cur = tgtNode;
        while(cur != terms[srcIdx]){
            int ei = dj[srcIdx].parentEdge[cur];
            if(ei == -1) break; // shouldn't happen in connected graph
            if(!B[ei]){
                B[ei] = 1;
                sumW += g.edges[ei].w;
            }
            int a = g.edges[ei].u;
            int b = g.edges[ei].v;
            cur = (a == cur ? b : a);
        }
    }
    return {B, sumW};
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if(!(cin >> N >> M >> K)){
        return 0;
    }
    vector<int> x(N+1), y(N+1);
    for(int i=1;i<=N;i++){
        cin >> x[i] >> y[i];
    }
    Graph g(N, M);
    for(int j=1;j<=M;j++){
        int u, v;
        long long w;
        cin >> u >> v >> w;
        g.add_edge(j, u, v, w);
    }
    vector<int> a(K), b(K);
    for(int k=0;k<K;k++){
        cin >> a[k] >> b[k];
    }

    // Precompute resident-to-station distances (ceil of Euclidean)
    // resDist[k*N + (i-1)]
    vector<int> resDist(K * N, 0);
    for(int k=0;k<K;k++){
        long long ak = a[k], bk = b[k];
        for(int i=1;i<=N;i++){
            long long dx = ak - x[i];
            long long dy = bk - y[i];
            long long sq = dx*dx + dy*dy;
            int d = ceil_isqrtll(sq);
            resDist[k*N + (i-1)] = d;
        }
    }

    auto eval_solution = [&](const vector<int> &selectedCenters)->tuple<vector<int>, vector<char>, long long, int>{
        // selectedCenters: list of station indices that will have P>0 (except maybe 1 if not selected)
        vector<int> P(N+1, 0);
        // Assign each resident to nearest selected center (if any within 5000). If no selected centers, nCovered = 0.
        int nCovered = 0;
        if(!selectedCenters.empty()){
            for(int k=0;k<K;k++){
                int bestI = -1;
                int bestD = INT_MAX;
                for(int idx=0; idx<(int)selectedCenters.size(); idx++){
                    int i = selectedCenters[idx];
                    int d = resDist[k*N + (i-1)];
                    if(d < bestD){
                        bestD = d;
                        bestI = i;
                    }
                }
                if(bestI != -1 && bestD <= 5000){
                    if(bestD > P[bestI]) P[bestI] = bestD;
                    nCovered++;
                }
            }
        }
        // Build terminals (must include 1 even if P1==0)
        vector<int> terms = selectedCenters;
        bool has1 = find(terms.begin(), terms.end(), 1) != terms.end();
        if(!has1) terms.push_back(1);
        sort(terms.begin(), terms.end());
        terms.erase(unique(terms.begin(), terms.end()), terms.end());
        // Connect terminals with metric MST -> get B and edge sum
        auto [B, sumEdge] = connect_terminals_metric_MST(g, terms);
        // Compute S cost
        long long sumP2 = 0;
        for(int i=1;i<=N;i++){
            long long p = P[i];
            sumP2 += p*p;
        }
        long long S = sumP2 + sumEdge;
        return {P, B, S, nCovered};
    };

    // Candidate 1: Selected centers = all N stations (to ensure each resident assigned to nearest center among all).
    vector<int> allCenters(N);
    iota(allCenters.begin(), allCenters.end(), 1);
    auto [P_all, B_all, S_all, n_all] = eval_solution(allCenters);

    // Candidate 2: Use nearest assignment to all N first, then only keep centers that got at least one assigned resident.
    vector<int> countAssigned(N+1, 0);
    for(int k=0;k<K;k++){
        int bestI = 1;
        int bestD = resDist[k*N + (1-1)];
        for(int i=2;i<=N;i++){
            int d = resDist[k*N + (i-1)];
            if(d < bestD){
                bestD = d;
                bestI = i;
            }
        }
        countAssigned[bestI]++;
    }
    vector<int> posCenters;
    posCenters.reserve(N);
    for(int i=1;i<=N;i++){
        if(countAssigned[i] > 0) posCenters.push_back(i);
    }
    auto [P_pos, B_pos, S_pos, n_pos] = eval_solution(posCenters);

    // Candidate 3: Greedy set cover with radius limit 5000
    vector<vector<int>> stationCover(N+1);
    for(int i=1;i<=N;i++){
        stationCover[i].reserve(K / N + 10);
    }
    for(int k=0;k<K;k++){
        for(int i=1;i<=N;i++){
            int d = resDist[k*N + (i-1)];
            if(d <= 5000) stationCover[i].push_back(k);
        }
    }
    vector<char> covered(K, 0);
    int remain = K;
    vector<char> selectedFlag(N+1, 0);
    // Greedy: repeatedly select station that covers most uncovered residents
    while(remain > 0){
        int bestI = -1;
        int bestGain = -1;
        // Break ties by distance from station to node 1 (approx connectivity)
        static const long long INF = (1LL<<62);
        long long bestTie = INF;
        // Precompute dijkstra from 1 for tie-breaking if needed
        // We'll compute once
        // But rather than recomputing each time, do here once
        // Actually computing once outside is ok. We'll compute on first usage.
        static bool computedFrom1 = false;
        static vector<long long> distFrom1;
        if(!computedFrom1){
            auto dj1 = dijkstra_from(g, 1);
            distFrom1 = dj1.dist;
            computedFrom1 = true;
        }
        for(int i=1;i<=N;i++){
            if(selectedFlag[i]) continue;
            int gain = 0;
            for(int kidx: stationCover[i]){
                if(!covered[kidx]) gain++;
            }
            if(gain > bestGain){
                bestGain = gain;
                bestI = i;
                bestTie = distFrom1[i];
            } else if(gain == bestGain){
                long long tie = distFrom1[i];
                if(tie < bestTie){
                    bestI = i;
                    bestTie = tie;
                }
            }
        }
        if(bestI == -1 || bestGain <= 0){
            // Fallback: pick the station closest to 1 that covers at least one uncovered resident, or any station
            long long bestT = INF;
            int iPick = -1;
            for(int i=1;i<=N;i++){
                if(selectedFlag[i]) continue;
                long long t = distFrom1[i];
                if(t < bestT){
                    bestT = t;
                    iPick = i;
                }
            }
            if(iPick == -1) break;
            bestI = iPick;
        }
        selectedFlag[bestI] = 1;
        for(int kidx: stationCover[bestI]){
            if(!covered[kidx]){
                covered[kidx] = 1;
                remain--;
            }
        }
    }
    vector<int> coverCenters;
    coverCenters.reserve(N);
    for(int i=1;i<=N;i++) if(selectedFlag[i]) coverCenters.push_back(i);
    auto [P_cov, B_cov, S_cov, n_cov] = eval_solution(coverCenters);

    // Choose best among candidates that cover all residents preferably; if multiple, pick minimal S.
    struct Cand {
        vector<int> P;
        vector<char> B;
        long long S;
        int n;
    };
    vector<Cand> cands;
    cands.push_back({move(P_all), move(B_all), S_all, n_all});
    cands.push_back({move(P_pos), move(B_pos), S_pos, n_pos});
    cands.push_back({move(P_cov), move(B_cov), S_cov, n_cov});

    // Prefer full coverage (n == K), choose minimal S among them; if none, choose max n, then minimal S
    int bestIdx = -1;
    long long bestS = (1LL<<62);
    int bestN = -1;
    for(int i=0;i<(int)cands.size();i++){
        int n = cands[i].n;
        long long S = cands[i].S;
        if(n > bestN){
            bestN = n;
            bestS = S;
            bestIdx = i;
        } else if(n == bestN){
            if(S < bestS){
                bestS = S;
                bestIdx = i;
            }
        }
    }

    auto &best = cands[bestIdx];

    // Output
    // P_1 ... P_N
    for(int i=1;i<=N;i++){
        int p = 0;
        if(i <= (int)best.P.size()-1) p = best.P[i];
        if(p < 0) p = 0;
        if(p > 5000) p = 5000;
        cout << p << (i==N?'\n':' ');
    }
    for(int j=1;j<=M;j++){
        int b = 0;
        if(j <= (int)best.B.size()-1) b = best.B[j];
        cout << b << (j==M?'\n':' ');
    }
    return 0;
}