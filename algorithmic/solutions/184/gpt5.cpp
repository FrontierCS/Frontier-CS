#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

struct Solver {
    int N;
    long long M;
    vector< bitset<MAXN> > adj;
    vector<vector<int>> g;
    mt19937_64 rng;
    chrono::steady_clock::time_point start;
    double timeLimit;

    Solver(int n, long long m): N(n), M(m), adj(n), g(n) {
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
        start = chrono::steady_clock::now();
        timeLimit = 1.90; // seconds
    }

    double elapsed() const {
        using namespace std::chrono;
        return duration_cast<duration<double>>(steady_clock::now() - start).count();
    }

    bitset<MAXN> greedy_min_degree() {
        bitset<MAXN> alive, sel;
        for (int i = 0; i < N; ++i) alive.set(i);
        while (alive.any()) {
            int bestDeg = INT_MAX;
            vector<int> candidates;
            for (int u = 0; u < N; ++u) {
                if (!alive[u]) continue;
                int deg = (int)((adj[u] & alive).count());
                if (deg < bestDeg) {
                    bestDeg = deg;
                    candidates.clear();
                    candidates.push_back(u);
                } else if (deg == bestDeg) {
                    candidates.push_back(u);
                }
            }
            int pick = candidates.size() == 1 ? candidates[0] : candidates[rng() % candidates.size()];
            sel.set(pick);
            bitset<MAXN> rem = adj[pick];
            rem.set(pick);
            alive &= ~rem;
        }
        return sel;
    }

    void augment(bitset<MAXN>& sel, vector<int>& conf) {
        queue<int> q;
        for (int v = 0; v < N; ++v) {
            if (!sel[v] && conf[v] == 0) q.push(v);
        }
        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (sel[v] || conf[v] != 0) continue;
            sel.set(v);
            for (int w : g[v]) {
                conf[w] += 1;
                // No need to push neighbors here since conf increases
            }
        }
    }

    bool improve_12(bitset<MAXN>& sel, vector<int>& conf) {
        // Try to find u in sel, and two vertices a, b not in sel, conf[a] = conf[b] = 1,
        // both only adjacent to u in sel, and a not adjacent to b.
        vector<int> Slist;
        Slist.reserve(N);
        for (int i = 0; i < N; ++i) if (sel[i]) Slist.push_back(i);

        // Randomize order to diversify
        shuffle(Slist.begin(), Slist.end(), rng);

        for (int u : Slist) {
            // Collect candidates adjacent to u with conf == 1
            vector<int> cands;
            cands.reserve(g[u].size());
            for (int v : g[u]) {
                if (!sel[v] && conf[v] == 1) {
                    // Since conf[v]==1 and u in sel and u is neighbor of v, u is the unique neighbor in sel
                    cands.push_back(v);
                }
            }
            if ((int)cands.size() < 2) continue;

            // Try to find a non-edge pair among cands
            // Limit quadratic checks to keep fast
            int limitChecks = 50000;
            int checks = 0;
            bool found = false;
            int a = -1, b = -1;

            // Shuffle to avoid deterministic behavior
            shuffle(cands.begin(), cands.end(), rng);

            for (int i = 0; i < (int)cands.size() && !found; ++i) {
                int vi = cands[i];
                for (int j = i + 1; j < (int)cands.size(); ++j) {
                    int vj = cands[j];
                    ++checks;
                    if (!adj[vi][vj]) {
                        a = vi; b = vj; found = true; break;
                    }
                    if (checks >= limitChecks) break;
                }
                if (checks >= limitChecks) break;
            }

            if (!found) continue;

            // Apply 1-2 improvement: remove u, add a and b
            sel.reset(u);
            for (int w : g[u]) conf[w] -= 1;
            // Now conf[a] and conf[b] should be 0 (they were 1, unique neighbor u removed)
            sel.set(a);
            for (int w : g[a]) conf[w] += 1;
            sel.set(b);
            for (int w : g[b]) conf[w] += 1;

            // Augment with any new free vertices
            augment(sel, conf);

            return true;
        }
        return false;
    }

    int compute_conf_single(int v, const bitset<MAXN>& sel) {
        int c = 0;
        for (int w : g[v]) if (sel[w]) ++c;
        return c;
    }

    vector<int> bits_to_output(const bitset<MAXN>& sel) {
        vector<int> out(N, 0);
        for (int i = 0; i < N; ++i) out[i] = sel[i] ? 1 : 0;
        return out;
    }

    void solve_and_output() {
        // Build adjacency list from bitsets (deduplicated by bitset)
        for (int u = 0; u < N; ++u) {
            g[u].reserve(16);
            for (int v = 0; v < N; ++v) {
                if (adj[u][v]) g[u].push_back(v);
            }
        }

        bitset<MAXN> bestSel;
        int bestK = -1;

        int attempts = 0;
        while (elapsed() < timeLimit) {
            ++attempts;

            bitset<MAXN> sel = greedy_min_degree();

            // Compute conflicts
            vector<int> conf(N, 0);
            for (int v = 0; v < N; ++v) {
                int c = 0;
                for (int w : g[v]) if (sel[w]) ++c;
                conf[v] = c;
            }

            // Augment if any zero-conf non-selected exist (should be none if greedy is maximal, but safe)
            augment(sel, conf);

            // Local search: 1-2 improvements while time left
            while (elapsed() < timeLimit) {
                bool improved = improve_12(sel, conf);
                if (!improved) break;
            }

            int K = (int)sel.count();
            if (K > bestK) {
                bestK = K;
                bestSel = sel;
            }

            // A small random shake: try a few 1-1 swaps to diversify, then re-augment
            if (elapsed() >= timeLimit) break;
            int shakeIters = 3;
            for (int it = 0; it < shakeIters && elapsed() < timeLimit; ++it) {
                // collect cand vertices with conf == 1
                vector<int> cand;
                for (int v = 0; v < N; ++v) if (!sel[v] && conf[v] == 1) cand.push_back(v);
                if (cand.empty()) continue;
                int v = cand[rng() % cand.size()];
                int uNeighbor = -1;
                for (int w : g[v]) if (sel[w]) { uNeighbor = w; break; }
                if (uNeighbor == -1) continue; // should not happen

                // perform swap uNeighbor out, v in
                sel.reset(uNeighbor);
                for (int w : g[uNeighbor]) conf[w] -= 1;

                if (conf[v] == 0) {
                    sel.set(v);
                    for (int w : g[v]) conf[w] += 1;
                } else {
                    // revert if cannot add (shouldn't happen since conf[v] should be 0 now)
                    sel.set(uNeighbor);
                    for (int w : g[uNeighbor]) conf[w] += 1;
                    continue;
                }

                // augment after shake
                augment(sel, conf);

                // try small number of 1-2 improvements
                int localSteps = 2;
                while (localSteps-- > 0 && elapsed() < timeLimit) {
                    if (!improve_12(sel, conf)) break;
                }

                int currK = (int)sel.count();
                if (currK > bestK) {
                    bestK = currK;
                    bestSel = sel;
                }
            }
        }

        // Output best found
        vector<int> out = bits_to_output(bestSel);
        for (int i = 0; i < N; ++i) {
            cout << out[i] << '\n';
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    Solver solver(N, M);
    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        solver.adj[u].set(v);
        solver.adj[v].set(u);
    }
    solver.solve_and_output();
    return 0;
}