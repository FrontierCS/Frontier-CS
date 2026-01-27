#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1005;

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
    for (int i = 0; i < N; ++i) adj[i].reset(i);
    // Build adjacency lists from bitsets (deduplicated)
    vector<vector<int>> nbrs(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (adj[i].test(j)) {
                nbrs[i].push_back(j);
                nbrs[j].push_back(i);
            }
        }
    }

    auto start = chrono::high_resolution_clock::now();
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    bitset<MAXN> bestS;
    int bestK = -1;

    auto elapsed_sec = [&](){
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    // Greedy builder (min degree in alive set with random tie-breaking)
    auto build_greedy = [&](bitset<MAXN>& Sbits){
        Sbits.reset();
        bitset<MAXN> alive;
        for (int i = 0; i < N; ++i) alive.set(i);
        while (alive.any()) {
            int minDeg = INT_MAX;
            int chosen = -1;
            int countSame = 0;
            for (int i = 0; i < N; ++i) {
                if (!alive.test(i)) continue;
                int d = (int)((adj[i] & alive).count());
                if (d < minDeg) {
                    minDeg = d;
                    chosen = i;
                    countSame = 1;
                } else if (d == minDeg) {
                    // reservoir sampling
                    ++countSame;
                    if (uniform_int_distribution<int>(1, countSame)(rng) == 1) {
                        chosen = i;
                    }
                }
            }
            if (chosen == -1) break;
            Sbits.set(chosen);
            alive.reset(chosen);
            alive &= ~adj[chosen];
        }
    };

    auto local_improve = [&](bitset<MAXN>& Sbits){
        // ns[u] = number of neighbors of u that are in S
        vector<int> ns(N, 0);
        for (int u = 0; u < N; ++u) {
            if (!Sbits.test(u)) continue;
            for (int v : nbrs[u]) ns[v]++;
        }
        bool improved = true;
        while (improved) {
            if (elapsed_sec() > 1.95) break;
            improved = false;
            for (int s = 0; s < N; ++s) {
                if (!Sbits.test(s)) continue;
                // Candidates: neighbors of s not in S with ns[u] == 1 (only s in S adjacent)
                vector<int> cand;
                for (int u : nbrs[s]) {
                    if (Sbits.test(u)) continue;
                    if (ns[u] == 1) cand.push_back(u);
                }
                // Try to find non-adjacent pair among cand
                bool done = false;
                int sz = (int)cand.size();
                for (int i = 0; i < sz && !done; ++i) {
                    for (int j = i + 1; j < sz; ++j) {
                        int a = cand[i], b = cand[j];
                        if (!adj[a].test(b)) {
                            // perform swap: remove s, add a and b
                            Sbits.reset(s);
                            for (int w : nbrs[s]) ns[w]--;
                            Sbits.set(a);
                            for (int w : nbrs[a]) ns[w]++;
                            Sbits.set(b);
                            for (int w : nbrs[b]) ns[w]++;
                            improved = true;
                            done = true;
                            break;
                        }
                    }
                }
                if (improved) break; // restart scanning
            }
        }
    };

    // Iterative multi-start within time limit
    while (elapsed_sec() < 1.98) {
        bitset<MAXN> S;
        build_greedy(S);
        local_improve(S);
        int k = (int)S.count();
        if (k > bestK) {
            bestK = k;
            bestS = S;
        }
        // small random perturbation by shuffling tie breaks will occur automatically next iteration
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestS.test(i) ? 1 : 0) << '\n';
    }
    return 0;
}