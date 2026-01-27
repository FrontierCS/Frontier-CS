#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now_millis() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

struct MISolver {
    int N;
    long long M;
    vector<vector<int>> g; // adjacency lists
    int B; // number of 64-bit blocks per bitset
    vector<vector<uint64_t>> adjBits; // adjacency bitsets
    mt19937_64 rng;
    uint64_t time_start;
    uint64_t time_limit_ms;

    MISolver(int n, long long m) : N(n), M(m) {
        g.assign(N, {});
        B = (N + 63) >> 6;
        adjBits.assign(N, vector<uint64_t>(B, 0ULL));
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
        time_start = now_millis();
        time_limit_ms = 1900; // aim to finish within ~1.9s
    }

    inline bool bit_get(const vector<uint64_t>& v, int i) const {
        return (v[i >> 6] >> (i & 63)) & 1ULL;
    }

    inline void bit_set(vector<uint64_t>& v, int i) {
        v[i >> 6] |= (1ULL << (i & 63));
    }

    inline void bit_clear(vector<uint64_t>& v, int i) {
        v[i >> 6] &= ~(1ULL << (i & 63));
    }

    inline void bit_and(const vector<uint64_t>& a, const vector<uint64_t>& b, vector<uint64_t>& res) const {
        for (int i = 0; i < B; ++i) res[i] = a[i] & b[i];
    }

    inline void bit_andnot(const vector<uint64_t>& a, const vector<uint64_t>& b, vector<uint64_t>& res) const {
        for (int i = 0; i < B; ++i) res[i] = a[i] & ~b[i];
    }

    inline int popcount_vec(const vector<uint64_t>& v) const {
        int s = 0;
        for (int i = 0; i < B; ++i) s += __builtin_popcountll(v[i]);
        return s;
    }

    inline int first_set_bit(const vector<uint64_t>& v) const {
        for (int i = 0; i < B; ++i) {
            if (v[i]) return (i << 6) + __builtin_ctzll(v[i]);
        }
        return -1;
    }

    inline void mask_clear_aboveN(vector<uint64_t>& v) const {
        int extra = (B << 6) - N;
        if (extra > 0) {
            uint64_t mask = (extra >= 64) ? 0ULL : (~0ULL >> extra);
            v[B - 1] &= mask;
        }
    }

    void add_edge(int u, int v) {
        if (u == v) return;
        if (!bit_get(adjBits[u], v)) {
            bit_set(adjBits[u], v);
            bit_set(adjBits[v], u);
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    vector<char> greedy_min_degree(bool randomize) {
        vector<char> sel(N, 0);
        vector<char> avail(N, 1);
        vector<int> degcur(N, 0);
        for (int i = 0; i < N; ++i) degcur[i] = (int)g[i].size();
        int avail_cnt = N;

        while (avail_cnt > 0) {
            int minDeg = INT_MAX;
            vector<int> cand;
            cand.reserve(N);
            for (int i = 0; i < N; ++i) {
                if (!avail[i]) continue;
                if (degcur[i] < minDeg) {
                    minDeg = degcur[i];
                    cand.clear();
                    cand.push_back(i);
                } else if (degcur[i] == minDeg) {
                    cand.push_back(i);
                }
            }
            if (cand.empty()) break;
            int v;
            if (randomize) {
                uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                v = cand[dist(rng)];
            } else {
                v = cand[0];
            }
            if (!avail[v]) continue;
            sel[v] = 1;
            avail[v] = 0;
            --avail_cnt;

            // remove neighbors of v
            for (int w : g[v]) {
                if (avail[w]) {
                    avail[w] = 0;
                    --avail_cnt;
                    // update degrees of neighbors of w
                    for (int x : g[w]) {
                        if (avail[x]) --degcur[x];
                    }
                }
            }
        }
        return sel;
    }

    int count_sel(const vector<char>& sel) const {
        int c = 0;
        for (int i = 0; i < N; ++i) if (sel[i]) ++c;
        return c;
    }

    void augment_maximal(vector<char>& sel, vector<int>& conf, vector<uint64_t>& cand1Mask) {
        bool changed = true;
        while (changed) {
            changed = false;
            for (int i = 0; i < N; ++i) {
                if (!sel[i] && conf[i] == 0) {
                    sel[i] = 1;
                    conf[i] = 0;
                    // clear from cand1
                    if (conf[i] == 1 && !sel[i]) bit_set(cand1Mask, i); else bit_clear(cand1Mask, i);
                    // update neighbors
                    for (int x : g[i]) {
                        if (!sel[x]) {
                            int before = conf[x];
                            ++conf[x];
                            // update cand1Mask for x
                            if (conf[x] == 1 && !sel[x]) bit_set(cand1Mask, x);
                            else bit_clear(cand1Mask, x);
                        }
                    }
                    changed = true;
                }
            }
        }
    }

    bool improve_once_2swap(vector<char>& sel) {
        // Build conf counts and cand1 mask
        vector<int> conf(N, 0);
        for (int s = 0; s < N; ++s) if (sel[s]) {
            for (int u : g[s]) ++conf[u];
        }
        vector<uint64_t> cand1Mask(B, 0ULL);
        for (int i = 0; i < N; ++i) {
            if (!sel[i] && conf[i] == 1) bit_set(cand1Mask, i);
        }

        vector<uint64_t> Tmask(B, 0ULL);
        vector<uint64_t> tmp(B, 0ULL);

        for (int v = 0; v < N; ++v) {
            if (!sel[v]) continue;
            // T = neighbors of v with conf==1
            bit_and(adjBits[v], cand1Mask, Tmask);
            int tsize = popcount_vec(Tmask);
            if (tsize >= 2) {
                // iterate u in T
                for (int bi = 0; bi < B; ++bi) {
                    uint64_t x = Tmask[bi];
                    while (x) {
                        int bt = __builtin_ctzll(x);
                        int u = (bi << 6) + bt;
                        if (u >= N) break;
                        // M = Tmask & ~Adj[u] with u removed
                        for (int j = 0; j < B; ++j) tmp[j] = Tmask[j] & ~adjBits[u][j];
                        bit_clear(tmp, u);
                        if (popcount_vec(tmp) > 0) {
                            int w = first_set_bit(tmp);
                            if (w < 0 || w >= N) { x &= x - 1; continue; }
                            // apply 2-for-1 swap: remove v, add u and w
                            sel[v] = 0;
                            // update conf for neighbors of v
                            for (int xnb : g[v]) {
                                // xnb cannot be selected as v is selected and MIS is independent
                                --conf[xnb];
                                if (!sel[xnb]) {
                                    if (conf[xnb] == 1) bit_set(cand1Mask, xnb);
                                    else bit_clear(cand1Mask, xnb);
                                }
                            }
                            // add u
                            sel[u] = 1;
                            conf[u] = 0;
                            bit_clear(cand1Mask, u);
                            for (int xnb : g[u]) {
                                if (!sel[xnb]) {
                                    ++conf[xnb];
                                    if (conf[xnb] == 1) bit_set(cand1Mask, xnb);
                                    else bit_clear(cand1Mask, xnb);
                                }
                            }
                            // add w
                            sel[w] = 1;
                            conf[w] = 0;
                            bit_clear(cand1Mask, w);
                            for (int xnb : g[w]) {
                                if (!sel[xnb]) {
                                    ++conf[xnb];
                                    if (conf[xnb] == 1) bit_set(cand1Mask, xnb);
                                    else bit_clear(cand1Mask, xnb);
                                }
                            }
                            // ensure v not in cand1 (likely conf[v] >= 2 now)
                            if (!sel[v]) {
                                if (conf[v] == 1) bit_set(cand1Mask, v);
                                else bit_clear(cand1Mask, v);
                            }

                            // augment to maximal by adding all free vertices (conf==0)
                            augment_maximal(sel, conf, cand1Mask);
                            return true;
                        }
                        x &= x - 1;
                    }
                }
            }
        }
        return false;
    }

    void improve_loop(vector<char>& sel) {
        // Repeat 2-improvement while possible and time allows
        int iter = 0;
        while (now_millis() - time_start < time_limit_ms) {
            bool improved = improve_once_2swap(sel);
            if (!improved) break;
            ++iter;
            if (iter > 10000) break; // safety
        }
    }

    vector<char> solve() {
        vector<char> best;
        int bestSize = -1;

        // Baseline deterministic and randomized runs
        vector<pair<bool,int>> plans;
        plans.push_back({false, 1}); // deterministic
        plans.push_back({true, 1});  // randomized

        // Run a number of randomized restarts while time allows
        int extraRestarts = 1000; // upper bound, will be cut by time
        for (int i = 0; i < extraRestarts; ++i) plans.push_back({true, 1});

        for (auto &pl : plans) {
            if (now_millis() - time_start > time_limit_ms) break;
            bool randomize = pl.first;
            vector<char> sel = greedy_min_degree(randomize);
            if (now_millis() - time_start > time_limit_ms) {
                int sz = count_sel(sel);
                if (sz > bestSize) { best = sel; bestSize = sz; }
                break;
            }
            improve_loop(sel);
            int sz = count_sel(sel);
            if (sz > bestSize) {
                best = sel;
                bestSize = sz;
            }
        }

        if (best.empty()) {
            // fallback: trivial greedy
            best = greedy_min_degree(true);
        }
        return best;
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
    MISolver solver(N, M);
    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N) continue;
        solver.add_edge(u, v);
    }
    vector<char> ans = solver.solve();
    for (int i = 0; i < N; ++i) {
        cout << (ans[i] ? 1 : 0) << '\n';
    }
    return 0;
}