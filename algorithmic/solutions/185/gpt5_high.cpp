#include <bits/stdc++.h>
using namespace std;

struct MaxCliqueSolver {
    int N, M;
    int W; // number of 64-bit words per bitset
    vector<vector<uint64_t>> adj; // adjacency bitsets
    vector<int> deg; // degrees
    vector<uint64_t> mask; // mask for valid bits (last word masked)
    mt19937 rng;

    MaxCliqueSolver(int n, int m) : N(n), M(m) {
        W = (N + 63) >> 6;
        adj.assign(N, vector<uint64_t>(W, 0));
        deg.assign(N, 0);
        mask.assign(W, ~0ULL);
        if (N % 64 != 0) {
            mask[W - 1] = (1ULL << (N % 64)) - 1;
        }
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        rng.seed(seed ^ (uint64_t)(uintptr_t(this)));
    }

    inline void set_edge(int u, int v) {
        uint64_t bitv = (1ULL << (v & 63));
        if ((adj[u][v >> 6] & bitv) == 0) {
            adj[u][v >> 6] |= bitv;
            adj[v][u >> 6] |= (1ULL << (u & 63));
            deg[u]++;
            deg[v]++;
        }
    }

    inline void setbit(vector<uint64_t>& b, int idx) const { b[idx >> 6] |= (1ULL << (idx & 63)); }
    inline void clearbit(vector<uint64_t>& b, int idx) const { b[idx >> 6] &= ~(1ULL << (idx & 63)); }
    inline bool testbit(const vector<uint64_t>& b, int idx) const { return (b[idx >> 6] >> (idx & 63)) & 1ULL; }

    inline int popcount_intersection(const vector<uint64_t>& a, const vector<uint64_t>& b) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i] & b[i]);
        return s;
    }

    inline void cand_intersect_with_adj(vector<uint64_t>& cand, int v) const {
        for (int i = 0; i < W; ++i) cand[i] &= adj[v][i];
    }

    inline void computeCandFromS(const vector<int>& Slist, vector<uint64_t>& cand) const {
        for (int i = 0; i < W; ++i) cand[i] = mask[i];
        for (int v : Slist) {
            for (int i = 0; i < W; ++i) cand[i] &= adj[v][i];
        }
    }

    int chooseBestFromCand(const vector<uint64_t>& cand) {
        int best = -1, sec = -1;
        int bestVal = -1, secVal = -1;
        int bestDeg = -1, secDeg = -1;

        for (int wi = 0; wi < W; ++wi) {
            uint64_t word = cand[wi];
            while (word) {
                uint64_t t = word & -word;
                int v = (wi << 6) + __builtin_ctzll(word);
                word ^= t;

                int s = popcount_intersection(adj[v], cand);
                int d = deg[v];
                if (s > bestVal || (s == bestVal && d > bestDeg)) {
                    sec = best; secVal = bestVal; secDeg = bestDeg;
                    best = v; bestVal = s; bestDeg = d;
                } else if (s > secVal || (s == secVal && d > secDeg)) {
                    sec = v; secVal = s; secDeg = d;
                }
            }
        }
        if (best == -1) return -1;
        if (sec != -1) {
            uniform_int_distribution<int> d(0, 99);
            if (d(rng) < 20) return sec; // 20% choose second best
        }
        return best;
    }

    void greedyExpand(vector<int>& Slist, vector<uint64_t>& Sbit) {
        vector<uint64_t> cand(W, 0);
        if (Slist.empty()) {
            for (int i = 0; i < W; ++i) cand[i] = mask[i];
        } else {
            computeCandFromS(Slist, cand);
        }
        while (true) {
            int v = chooseBestFromCand(cand);
            if (v == -1) break;
            Slist.push_back(v);
            setbit(Sbit, v);
            cand_intersect_with_adj(cand, v);
        }
    }

    vector<int> buildFromStart(int v0) {
        vector<int> Slist;
        Slist.reserve(64);
        vector<uint64_t> Sbit(W, 0);

        Slist.push_back(v0);
        setbit(Sbit, v0);

        vector<uint64_t> cand = adj[v0];
        while (true) {
            int v = chooseBestFromCand(cand);
            if (v == -1) break;
            Slist.push_back(v);
            setbit(Sbit, v);
            cand_intersect_with_adj(cand, v);
        }
        return Slist;
    }

    bool plateauImprove(vector<int>& Slist, vector<uint64_t>& Sbit) {
        bool improved = false;
        while (true) {
            bool swapped = false;
            for (int u = 0; u < N; ++u) {
                if (testbit(Sbit, u)) continue;
                int missing = 0;
                int w_missing = -1;
                for (int i = 0; i < W; ++i) {
                    uint64_t x = Sbit[i] & (~adj[u][i] & mask[i]);
                    int c = __builtin_popcountll(x);
                    if (c) {
                        if (missing + c > 1) { missing = 2; break; }
                        int idx = (i << 6) + __builtin_ctzll(x);
                        w_missing = idx;
                        missing += c;
                    }
                }
                if (missing == 1) {
                    int posw = -1;
                    for (int i = 0; i < (int)Slist.size(); ++i) {
                        if (Slist[i] == w_missing) { posw = i; break; }
                    }
                    if (posw != -1) {
                        int last = Slist.back();
                        Slist[posw] = last;
                        Slist.pop_back();
                        clearbit(Sbit, w_missing);
                        Slist.push_back(u);
                        setbit(Sbit, u);
                        greedyExpand(Slist, Sbit);
                        swapped = true;
                        improved = true;
                        break;
                    }
                }
            }
            if (!swapped) break;
        }
        return improved;
    }

    vector<int> solve(double time_limit_sec = 1.85) {
        vector<int> bestS;
        int bestSize = 0;

        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            return deg[a] > deg[b];
        });

        auto t0 = chrono::steady_clock::now();
        auto deadline = t0 + chrono::duration<double>(time_limit_sec);

        for (int idx = 0; idx < N; ++idx) {
            int v0 = order[idx];
            vector<int> S = buildFromStart(v0);
            vector<uint64_t> Sbit(W, 0);
            for (int v : S) setbit(Sbit, v);
            plateauImprove(S, Sbit);
            if ((int)S.size() > bestSize) {
                bestSize = (int)S.size();
                bestS = S;
            }
            if (chrono::steady_clock::now() > deadline) break;
        }

        uniform_int_distribution<int> distV(0, N - 1);
        while (chrono::steady_clock::now() < deadline) {
            int v0 = distV(rng);
            vector<int> S = buildFromStart(v0);
            vector<uint64_t> Sbit(W, 0);
            for (int v : S) setbit(Sbit, v);
            plateauImprove(S, Sbit);
            if ((int)S.size() > bestSize) {
                bestSize = (int)S.size();
                bestS = S;
            }
        }

        if (bestS.empty()) {
            int bestv = 0;
            for (int i = 1; i < N; ++i) if (deg[i] > deg[bestv]) bestv = i;
            bestS.push_back(bestv);
        }
        return bestS;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    MaxCliqueSolver solver(N, M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u >= 0 && u < N && v >= 0 && v < N && u != v) {
            solver.set_edge(u, v);
        }
    }
    vector<int> clique = solver.solve();
    vector<int> ans(N, 0);
    for (int v : clique) ans[v] = 1;
    for (int i = 0; i < N; ++i) {
        cout << ans[i] << '\n';
    }
    return 0;
}