#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    const int MAXN = 1005;
    static bitset<MAXN> adj[MAXN];
    for (int i = 0; i < N; ++i) {
        adj[i].reset();
        adj[i].set(i, false);
    }
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].count();
    
    // Time-bounded randomized greedy heuristic
    using clk = chrono::steady_clock;
    auto start = clk::now();
    const double TIME_LIMIT = 1.8; // seconds
    
    vector<int> bestClique;
    vector<int> currentClique;
    bitset<MAXN> Cand;
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto elapsed = [&]() -> double {
        return chrono::duration<double>(clk::now() - start).count();
    };
    
    // Pre-build list of all vertices
    vector<int> vertices(N);
    iota(vertices.begin(), vertices.end(), 0);
    
    // A simple deterministic attempt first (degree-based)
    {
        Cand.reset();
        for (int i = 0; i < N; ++i) Cand.set(i);
        currentClique.clear();
        while (Cand.any()) {
            int best = -1;
            int bestScore = -1;
            // Choose vertex with max (neighbors within Cand)
            for (int v = Cand._Find_first(); v < N; v = Cand._Find_next(v)) {
                int sc = (int)(adj[v] & Cand).count();
                if (sc > bestScore || (sc == bestScore && deg[v] > (best==-1? -1:deg[best]))) {
                    bestScore = sc;
                    best = v;
                }
            }
            if (best == -1) break;
            currentClique.push_back(best);
            Cand &= adj[best];
        }
        bestClique = currentClique;
    }
    
    // Randomized restarts until time limit
    while (elapsed() < TIME_LIMIT) {
        Cand.reset();
        for (int i = 0; i < N; ++i) Cand.set(i);
        currentClique.clear();
        
        // Small randomness in the process
        const int TOP_K = 3;
        while (Cand.any()) {
            // Find up to TOP_K best candidates
            array<pair<int,int>, 16> top; // (score, vertex), size >= TOP_K
            int kept = 0;
            for (int v = Cand._Find_first(); v < N; v = Cand._Find_next(v)) {
                int sc = (int)(adj[v] & Cand).count();
                if (kept < (int)top.size()) {
                    top[kept++] = {sc, v};
                } else {
                    // Keep best of top array
                    int minIdx = 0;
                    for (int i = 1; i < kept; ++i)
                        if (top[i].first < top[minIdx].first ||
                           (top[i].first == top[minIdx].first && deg[top[i].second] < deg[top[minIdx].second]))
                            minIdx = i;
                    if (sc > top[minIdx].first || (sc == top[minIdx].first && deg[v] > deg[top[minIdx].second])) {
                        top[minIdx] = {sc, v};
                    }
                }
            }
            if (kept == 0) break;
            // Sort kept top by score desc then degree desc
            sort(top.begin(), top.begin() + kept, [&](const auto& a, const auto& b){
                if (a.first != b.first) return a.first > b.first;
                return deg[a.second] > deg[b.second];
            });
            int pickRange = min(TOP_K, kept);
            int chosenIdx = uniform_int_distribution<int>(0, pickRange - 1)(rng);
            int v = top[chosenIdx].second;
            currentClique.push_back(v);
            Cand &= adj[v];
        }
        if (currentClique.size() > bestClique.size()) bestClique = currentClique;
    }
    
    vector<int> inC(N, 0);
    for (int v : bestClique) inC[v] = 1;
    
    // Output
    for (int i = 0; i < N; ++i) {
        cout << inC[i] << '\n';
    }
    return 0;
}