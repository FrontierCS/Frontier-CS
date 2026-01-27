#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 1000;
static constexpr int W = (MAXN + 63) / 64;

using Bits = array<uint64_t, W>;

static inline void set_bit(Bits &b, int v) {
    b[v >> 6] |= (1ULL << (v & 63));
}
static inline void clear_bit(Bits &b, int v) {
    b[v >> 6] &= ~(1ULL << (v & 63));
}
static inline bool test_bit(const Bits &b, int v) {
    return (b[v >> 6] >> (v & 63)) & 1ULL;
}
static inline bool empty_bits(const Bits &b, int words) {
    for (int i = 0; i < words; ++i) if (b[i]) return false;
    return true;
}
static inline int popcount_bits(const Bits &b, int words) {
    int s = 0;
    for (int i = 0; i < words; ++i) s += __builtin_popcountll(b[i]);
    return s;
}
static inline int popcount_and(const Bits &a, const Bits &b, int words) {
    int s = 0;
    for (int i = 0; i < words; ++i) s += __builtin_popcountll(a[i] & b[i]);
    return s;
}
static inline void and_inplace(Bits &a, const Bits &b, int words) {
    for (int i = 0; i < words; ++i) a[i] &= b[i];
}
static inline Bits and_bits(const Bits &a, const Bits &b, int words) {
    Bits r{};
    for (int i = 0; i < words; ++i) r[i] = a[i] & b[i];
    return r;
}

struct Solver {
    int N, M;
    int words;
    uint64_t lastMask;
    vector<Bits> adj;
    vector<int> deg;
    vector<int> order; // vertices sorted by degree desc
    Bits fullset{};
    mt19937 rng;

    Solver(int n, int m) : N(n), M(m) {
        words = (N + 63) / 64;
        int rem = N & 63;
        lastMask = rem ? ((1ULL << rem) - 1ULL) : ~0ULL;
        adj.assign(N, Bits{});
        deg.assign(N, 0);
        rng.seed((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        for (int i = 0; i < words; ++i) fullset[i] = ~0ULL;
        fullset[words - 1] &= lastMask;
        for (int i = words; i < W; ++i) fullset[i] = 0ULL;
    }

    inline int rand_int(int l, int r) { // inclusive
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    }

    int choose_vertex_from_cand(const Bits &cand) {
        // pick among top few by score (popcount(adj[v] & cand))
        int bestV = -1, bestS = -1;

        int topV[4] = {-1, -1, -1, -1};
        int topS[4] = {-1, -1, -1, -1};
        int topSz = 0;

        for (int wi = 0; wi < words; ++wi) {
            uint64_t x = cand[wi];
            while (x) {
                int b = __builtin_ctzll(x);
                int v = (wi << 6) + b;
                x &= x - 1;

                int sc = popcount_and(adj[v], cand, words);
                if (sc > bestS || (sc == bestS && (rng() & 1))) {
                    bestS = sc;
                    bestV = v;
                }

                // maintain small top list (size <= 4)
                int pos = topSz;
                if (pos < 4) {
                    topV[pos] = v;
                    topS[pos] = sc;
                    topSz++;
                } else {
                    // replace worst if better
                    int worst = 0;
                    for (int i = 1; i < 4; ++i)
                        if (topS[i] < topS[worst]) worst = i;
                    if (sc > topS[worst]) {
                        topV[worst] = v;
                        topS[worst] = sc;
                    }
                }
            }
        }

        if (bestV == -1) return -1;

        int r = (int)(rng() % 100);
        if (topSz > 1 && r < 35) {
            // choose randomly among best 2-3 in top list by score
            vector<pair<int,int>> tmp;
            tmp.reserve(topSz);
            for (int i = 0; i < topSz; ++i) if (topV[i] != -1) tmp.push_back({topS[i], topV[i]});
            sort(tmp.begin(), tmp.end(), [](auto &a, auto &b){ return a.first > b.first; });
            int take = min(3, (int)tmp.size());
            int idx = rand_int(0, take - 1);
            return tmp[idx].second;
        }
        return bestV;
    }

    vector<int> greedy_from_seed(int seed, bool usePair) {
        vector<int> clique;
        clique.reserve(64);

        Bits cand{};

        if (usePair) {
            // choose a good neighbor t of seed (max degree, slight random among top)
            int bestT = -1, bestD = -1;
            int topT[4] = {-1,-1,-1,-1};
            int topD[4] = {-1,-1,-1,-1};
            int topSz = 0;

            const Bits &ns = adj[seed];
            for (int wi = 0; wi < words; ++wi) {
                uint64_t x = ns[wi];
                while (x) {
                    int b = __builtin_ctzll(x);
                    int t = (wi << 6) + b;
                    x &= x - 1;
                    int d = deg[t];

                    if (d > bestD || (d == bestD && (rng() & 1))) {
                        bestD = d;
                        bestT = t;
                    }

                    int pos = topSz;
                    if (pos < 4) {
                        topT[pos] = t;
                        topD[pos] = d;
                        topSz++;
                    } else {
                        int worst = 0;
                        for (int i = 1; i < 4; ++i)
                            if (topD[i] < topD[worst]) worst = i;
                        if (d > topD[worst]) {
                            topT[worst] = t;
                            topD[worst] = d;
                        }
                    }
                }
            }

            if (bestT != -1) {
                int r = (int)(rng() % 100);
                if (topSz > 1 && r < 40) {
                    vector<pair<int,int>> tmp;
                    tmp.reserve(topSz);
                    for (int i = 0; i < topSz; ++i) if (topT[i] != -1) tmp.push_back({topD[i], topT[i]});
                    sort(tmp.begin(), tmp.end(), [](auto &a, auto &b){ return a.first > b.first; });
                    int take = min(3, (int)tmp.size());
                    bestT = tmp[rand_int(0, take - 1)].second;
                }

                clique.push_back(seed);
                clique.push_back(bestT);
                cand = and_bits(adj[seed], adj[bestT], words);
                clear_bit(cand, seed);
                clear_bit(cand, bestT);
            } else {
                clique.push_back(seed);
                cand = adj[seed];
                clear_bit(cand, seed);
            }
        } else {
            clique.push_back(seed);
            cand = adj[seed];
            clear_bit(cand, seed);
        }

        while (!empty_bits(cand, words)) {
            int v = choose_vertex_from_cand(cand);
            if (v < 0) break;
            clique.push_back(v);
            and_inplace(cand, adj[v], words);
            clear_bit(cand, v);
        }

        return clique;
    }

    vector<int> expand_from_clique(const vector<int> &base) {
        vector<int> clique = base;
        Bits cbits{};
        for (int v : clique) set_bit(cbits, v);

        Bits cand = fullset;
        for (int v : clique) and_inplace(cand, adj[v], words);

        // remove clique vertices from candidates
        for (int wi = 0; wi < words; ++wi) cand[wi] &= ~cbits[wi];
        cand[words - 1] &= lastMask;

        while (!empty_bits(cand, words)) {
            int v = choose_vertex_from_cand(cand);
            if (v < 0) break;
            clique.push_back(v);
            set_bit(cbits, v);
            and_inplace(cand, adj[v], words);
            clear_bit(cand, v);
        }
        return clique;
    }

    vector<int> improve_1swap(vector<int> clique, const vector<int> &degOrder, chrono::high_resolution_clock::time_point t0, double timeLimitSec) {
        Bits cbits{};
        for (int v : clique) set_bit(cbits, v);

        bool improved = true;
        while (improved) {
            improved = false;

            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - t0).count();
            if (elapsed > timeLimitSec) break;

            // Try add directly (shouldn't exist if maximal, but after swaps maybe)
            for (int u : degOrder) {
                if (test_bit(cbits, u)) continue;
                bool ok = true;
                for (int wi = 0; wi < words; ++wi) {
                    if ((cbits[wi] & ~adj[u][wi]) != 0ULL) { ok = false; break; }
                }
                if (ok) {
                    clique.push_back(u);
                    set_bit(cbits, u);
                    clique = expand_from_clique(clique);
                    cbits = Bits{};
                    for (int v : clique) set_bit(cbits, v);
                    improved = true;
                    break;
                }
            }
            if (improved) continue;

            // 1-swap: for outside u, if it misses exactly 1 vertex in clique, try swap and expand
            for (int u : degOrder) {
                if (test_bit(cbits, u)) continue;

                int missingCnt = 0;
                int missingV = -1;

                for (int wi = 0; wi < words; ++wi) {
                    uint64_t miss = cbits[wi] & ~adj[u][wi];
                    while (miss) {
                        int b = __builtin_ctzll(miss);
                        missingV = (wi << 6) + b;
                        miss &= miss - 1;
                        if (++missingCnt > 1) break;
                    }
                    if (missingCnt > 1) break;
                }
                if (missingCnt != 1) continue;

                vector<int> base;
                base.reserve(clique.size());
                for (int v : clique) if (v != missingV) base.push_back(v);
                base.push_back(u);

                vector<int> candClique = expand_from_clique(base);
                if (candClique.size() > clique.size()) {
                    clique.swap(candClique);
                    cbits = Bits{};
                    for (int v : clique) set_bit(cbits, v);
                    improved = true;
                    break;
                }

                now = chrono::high_resolution_clock::now();
                elapsed = chrono::duration<double>(now - t0).count();
                if (elapsed > timeLimitSec) break;
            }
        }
        return clique;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    Solver solver(N, M);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        set_bit(solver.adj[u], v);
        set_bit(solver.adj[v], u);
    }

    for (int i = 0; i < N; ++i) {
        int d = 0;
        for (int w = 0; w < solver.words; ++w) d += __builtin_popcountll(solver.adj[i][w]);
        solver.deg[i] = d;
    }

    solver.order.resize(N);
    iota(solver.order.begin(), solver.order.end(), 0);
    sort(solver.order.begin(), solver.order.end(), [&](int a, int b){
        if (solver.deg[a] != solver.deg[b]) return solver.deg[a] > solver.deg[b];
        return a < b;
    });

    vector<int> bestClique;
    bestClique.reserve(128);

    auto t0 = chrono::high_resolution_clock::now();
    const double MAIN_LIMIT = 1.78; // seconds, keep margin
    int it = 0;

    // Initial best: start from top degree
    if (N > 0) {
        int seed = solver.order[0];
        bestClique = solver.greedy_from_seed(seed, true);
        if (bestClique.empty()) bestClique.push_back(seed);
    }

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed > MAIN_LIMIT) break;

        int seed;
        if (it < min(N, 160)) {
            seed = solver.order[it];
        } else {
            int r = (int)(solver.rng() % 100);
            if (!bestClique.empty() && r < 45) {
                seed = bestClique[solver.rng() % bestClique.size()];
            } else if (r < 85) {
                seed = solver.order[solver.rng() % min(N, 250)];
            } else {
                seed = (int)(solver.rng() % N);
            }
        }

        bool usePair = ((solver.rng() & 1) != 0);
        vector<int> clique = solver.greedy_from_seed(seed, usePair);

        if (clique.size() > bestClique.size()) bestClique.swap(clique);

        ++it;
    }

    // Improve best clique with 1-swap local search if time remains
    {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed < 1.93) {
            bestClique = solver.improve_1swap(bestClique, solver.order, t0, 1.93);
        }
    }

    vector<int> out(N, 0);
    for (int v : bestClique) if (0 <= v && v < N) out[v] = 1;
    for (int i = 0; i < N; ++i) {
        cout << out[i] << "\n";
    }
    return 0;
}