#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector< bitset<MAXN> > adj(N);
    for (int i = 0; i < N; ++i) adj[i].reset();
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    for (int i = 0; i < N; ++i) adj[i].reset(i); // no self loops
    
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].count();
    
    vector<int> nodes(N);
    iota(nodes.begin(), nodes.end(), 0);
    sort(nodes.begin(), nodes.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });
    
    auto start_time = chrono::steady_clock::now();
    auto time_elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - start_time).count();
    };
    double time_limit = 1.90; // seconds, slightly under TL
    
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    
    vector<int> bestClique;
    vector<char> inBest(N, 0);
    
    auto greedy_from_seed = [&](int seed)->vector<int> {
        vector<int> clique;
        clique.reserve(N);
        bitset<MAXN> C = adj[seed];
        clique.push_back(seed);
        
        const int smallCThresh = 64;
        const int topK = 6;
        
        while (C.any()) {
            int chosen = -1;
            if ((int)C.count() <= smallCThresh) {
                // choose by highest degree within C
                int bestScore = -1;
                array<pair<int,int>, topK> topArr;
                int topSz = 0;
                for (int j = 0; j < N; ++j) if (C.test(j)) {
                    int sc = (int)( (adj[j] & C).count() );
                    if (topSz < topK) {
                        topArr[topSz++] = {sc, j};
                        // maintain min-heap-like by keeping smallest at position 0 via linear pass
                        int minPos = 0;
                        for (int t = 1; t < topSz; ++t) if (topArr[t].first < topArr[minPos].first) minPos = t;
                        // place smallest at index 0
                        if (minPos != 0) swap(topArr[0], topArr[minPos]);
                    } else {
                        if (sc > topArr[0].first) {
                            topArr[0] = {sc, j};
                            // re-find smallest
                            int minPos = 0;
                            for (int t = 1; t < topSz; ++t) if (topArr[t].first < topArr[minPos].first) minPos = t;
                            if (minPos != 0) swap(topArr[0], topArr[minPos]);
                        }
                    }
                }
                // pick random among topArr[0..topSz-1]
                if (topSz > 0) {
                    uniform_int_distribution<int> dist(0, topSz - 1);
                    int idx = dist(rng);
                    chosen = topArr[idx].second;
                } else {
                    break;
                }
            } else {
                // choose by highest global degree among C, random among topK
                array<pair<int,int>, topK> topArr;
                int topSz = 0;
                for (int j = 0; j < N; ++j) if (C.test(j)) {
                    int dj = deg[j];
                    if (topSz < topK) {
                        topArr[topSz++] = {dj, j};
                        int minPos = 0;
                        for (int t = 1; t < topSz; ++t) if (topArr[t].first < topArr[minPos].first) minPos = t;
                        if (minPos != 0) swap(topArr[0], topArr[minPos]);
                    } else {
                        if (dj > topArr[0].first) {
                            topArr[0] = {dj, j};
                            int minPos = 0;
                            for (int t = 1; t < topSz; ++t) if (topArr[t].first < topArr[minPos].first) minPos = t;
                            if (minPos != 0) swap(topArr[0], topArr[minPos]);
                        }
                    }
                }
                if (topSz > 0) {
                    uniform_int_distribution<int> dist(0, topSz - 1);
                    int idx = dist(rng);
                    chosen = topArr[idx].second;
                } else {
                    break;
                }
            }
            if (chosen == -1) break;
            clique.push_back(chosen);
            C &= adj[chosen];
        }
        return clique;
    };
    
    auto update_best = [&](const vector<int>& clq){
        if ((int)clq.size() > (int)bestClique.size()) {
            bestClique = clq;
        }
    };
    
    // First pass: try seeds in degree order
    for (int v : nodes) {
        if (time_elapsed() > time_limit) break;
        if (deg[v] == 0 && !bestClique.empty()) continue; // cannot improve unless best is empty
        vector<int> clq = greedy_from_seed(v);
        update_best(clq);
    }
    
    // Random restarts while time remains
    uniform_int_distribution<int> nodeDist(0, N - 1);
    while (time_elapsed() <= time_limit) {
        int v = nodeDist(rng);
        if (deg[v] == 0 && !bestClique.empty()) continue;
        vector<int> clq = greedy_from_seed(v);
        update_best(clq);
    }
    
    // Fallback in worst case
    if (bestClique.empty()) {
        // Pick an edge if exists, else single node
        int u = -1, v = -1;
        for (int i = 0; i < N && u == -1; ++i) {
            for (int j = i+1; j < N; ++j) {
                if (adj[i].test(j)) { u = i; v = j; break; }
            }
        }
        if (u != -1) {
            bestClique = {u, v};
        } else {
            bestClique = {0};
        }
    }
    
    vector<int> ans(N, 0);
    for (int x : bestClique) ans[x] = 1;
    for (int i = 0; i < N; ++i) {
        cout << ans[i] << '\n';
    }
    return 0;
}