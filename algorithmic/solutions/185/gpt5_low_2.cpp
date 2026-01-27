#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1050;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<bitset<MAXN>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].count();

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto grow_from = [&](const vector<int>& seed)->vector<int>{
        bitset<MAXN> cliqueBits;
        bitset<MAXN> candidates;
        candidates.set(); // start with all
        for (int v : seed) {
            cliqueBits.set(v);
            candidates &= adj[v];
        }
        // Remove existing clique vertices from candidates just in case
        candidates &= ~cliqueBits;

        // Greedy expansion
        while (candidates.any()) {
            int best = -1;
            int bestScore = -1;
            int bestDeg = -1;
            // Collect top few candidates
            vector<pair<int,int>> top; // (score, vertex)
            for (int v = 0; v < N; ++v) if (candidates.test(v)) {
                int score = (int)( (adj[v] & candidates).count() );
                if ((int)top.size() < 8) {
                    top.emplace_back(score, v);
                    push_heap(top.begin(), top.end(), [](auto &a, auto &b){ return a.first > b.first; });
                } else if (score > top.front().first) {
                    pop_heap(top.begin(), top.end(), [](auto &a, auto &b){ return a.first > b.first; });
                    top.back() = {score, v};
                    push_heap(top.begin(), top.end(), [](auto &a, auto &b){ return a.first > b.first; });
                }
                if (score > bestScore || (score == bestScore && deg[v] > bestDeg)) {
                    bestScore = score;
                    bestDeg = deg[v];
                    best = v;
                }
            }
            int chosen = best;
            if (!top.empty()) {
                // pick among top 3 with some randomness to diversify
                vector<pair<int,int>> cand = top;
                sort(cand.begin(), cand.end(), [](auto &a, auto &b){ return a.first > b.first; });
                int k = min(3, (int)cand.size());
                uniform_int_distribution<int> dist(0, k-1);
                if (rng() % 5 == 0) { // 20% chance
                    chosen = cand[dist(rng)].second;
                } else {
                    chosen = cand[0].second;
                }
            }
            cliqueBits.set(chosen);
            candidates &= adj[chosen];
            candidates.reset(chosen);
        }

        vector<int> res;
        for (int i = 0; i < N; ++i) if (cliqueBits.test(i)) res.push_back(i);
        return res;
    };

    vector<int> bestClique;
    auto start_time = chrono::high_resolution_clock::now();
    auto elapsed = [&](){
        return chrono::duration<double>(chrono::high_resolution_clock::now() - start_time).count();
    };

    // Try seeds based on highest degree
    int max_seeds = min(N, 300);
    for (int i = 0; i < max_seeds; ++i) {
        if (elapsed() > 1.8) break;
        vector<int> seed = {order[i]};
        auto c = grow_from(seed);
        if (c.size() > bestClique.size()) bestClique = move(c);
    }

    // Random restarts from random vertices
    vector<int> vertices(N);
    iota(vertices.begin(), vertices.end(), 0);
    for (int iter = 0; iter < 10000; ++iter) {
        if (elapsed() > 1.95) break;
        int v = vertices[rng() % N];
        vector<int> seed = {v};
        auto c = grow_from(seed);
        if (c.size() > bestClique.size()) bestClique = move(c);
    }

    // Output
    vector<int> in(N, 0);
    for (int v : bestClique) in[v] = 1;
    for (int i = 0; i < N; ++i) {
        cout << in[i] << "\n";
    }

    return 0;
}