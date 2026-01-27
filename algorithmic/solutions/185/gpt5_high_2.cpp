#include <bits/stdc++.h>
using namespace std;

using ULL = unsigned long long;

struct MaxCliqueSolver {
    int N, M;
    int B; // number of 64-bit blocks
    vector<vector<ULL>> adj; // adjacency bitset per vertex
    vector<int> deg;
    vector<ULL> ALL; // all ones in first N bits
    ULL lastMask; // mask for last block
    mt19937_64 rng;

    MaxCliqueSolver(int n, int m): N(n), M(m) {
        B = (N + 63) / 64;
        adj.assign(N, vector<ULL>(B, 0));
        deg.assign(N, 0);
        ALL.assign(B, ~0ULL);
        int rem = N % 64;
        if (rem == 0) lastMask = ~0ULL;
        else lastMask = (rem == 64 ? ~0ULL : ((1ULL << rem) - 1));
        if (B > 0) ALL[B-1] &= lastMask;
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    inline void set_edge(int u, int v) {
        adj[u][v >> 6] |= (1ULL << (v & 63));
    }

    inline bool bit_test(const vector<ULL>& bs, int i) const {
        return (bs[i >> 6] >> (i & 63)) & 1ULL;
    }

    inline void bit_set(vector<ULL>& bs, int i) {
        bs[i >> 6] |= (1ULL << (i & 63));
    }

    inline void bit_clear(vector<ULL>& bs, int i) {
        bs[i >> 6] &= ~(1ULL << (i & 63));
    }

    inline bool is_zero(const vector<ULL>& bs) const {
        for (int i = 0; i < B; ++i) if (bs[i]) return false;
        return true;
    }

    inline int popcount_intersection(const vector<ULL>& a, const vector<ULL>& b) const {
        int s = 0;
        for (int i = 0; i < B; ++i) s += __builtin_popcountll(a[i] & b[i]);
        return s;
    }

    inline void and_with(vector<ULL>& a, const vector<ULL>& b) const {
        for (int i = 0; i < B; ++i) a[i] &= b[i];
    }

    inline vector<int> list_bits(const vector<ULL>& bs) const {
        vector<int> res;
        res.reserve(N);
        for (int i = 0; i < B; ++i) {
            ULL w = bs[i];
            while (w) {
                int t = __builtin_ctzll(w);
                res.push_back((i << 6) + t);
                w &= w - 1;
            }
        }
        return res;
    }

    void compute_degrees() {
        for (int i = 0; i < N; ++i) {
            int s = 0;
            for (int j = 0; j < B; ++j) s += __builtin_popcountll(adj[i][j]);
            deg[i] = s;
        }
    }

    pair<vector<int>, vector<ULL>> greedy_from_seed(int seed) {
        vector<ULL> C(B, 0), Sset(B, 0);
        vector<int> Slist;
        if (seed >= 0) {
            bit_set(Sset, seed);
            C = adj[seed];
        } else {
            C = ALL;
        }

        while (!is_zero(C)) {
            vector<int> cand = list_bits(C);
            int bestV = -1;
            int bestScore = -1;
            int tieCount = 0;
            for (int v : cand) {
                int score = 0;
                for (int i = 0; i < B; ++i) score += __builtin_popcountll(C[i] & adj[v][i]);
                if (score > bestScore) {
                    bestScore = score;
                    bestV = v;
                    tieCount = 1;
                } else if (score == bestScore) {
                    ++tieCount;
                    // random tie-breaking
                    if ((rng() % tieCount) == 0) bestV = v;
                }
            }
            if (bestV == -1) break;
            Slist.push_back(bestV);
            bit_set(Sset, bestV);
            for (int i = 0; i < B; ++i) C[i] &= adj[bestV][i];
        }
        return {Slist, Sset};
    }

    pair<vector<int>, vector<ULL>> greedy_extend_from_clique(const vector<ULL>& initSset) {
        vector<ULL> Sset = initSset;
        vector<int> Slist = list_bits(Sset);
        vector<ULL> C = ALL;
        for (int v : Slist) for (int i = 0; i < B; ++i) C[i] &= adj[v][i];
        while (!is_zero(C)) {
            vector<int> cand = list_bits(C);
            int bestV = -1;
            int bestScore = -1;
            int tieCount = 0;
            for (int v : cand) {
                int score = 0;
                for (int i = 0; i < B; ++i) score += __builtin_popcountll(C[i] & adj[v][i]);
                if (score > bestScore) {
                    bestScore = score;
                    bestV = v;
                    tieCount = 1;
                } else if (score == bestScore) {
                    ++tieCount;
                    if ((rng() % tieCount) == 0) bestV = v;
                }
            }
            if (bestV == -1) break;
            Slist.push_back(bestV);
            bit_set(Sset, bestV);
            for (int i = 0; i < B; ++i) C[i] &= adj[bestV][i];
        }
        return {Slist, Sset};
    }

    bool improve_1swap_once(vector<int>& bestList, vector<ULL>& bestSet, const chrono::steady_clock::time_point& deadline) {
        int K = (int)bestList.size();
        // Scan vertices not in bestSet
        for (int u = 0; u < N; ++u) {
            if (chrono::steady_clock::now() > deadline) return false;
            if (bit_test(bestSet, u)) continue;
            int inter = popcount_intersection(bestSet, adj[u]);
            if (K - inter == 1) {
                // find missing vertex w
                int wIdx = -1;
                for (int i = 0; i < B; ++i) {
                    ULL miss = bestSet[i] & (~adj[u][i]);
                    if (miss) {
                        int t = __builtin_ctzll(miss);
                        wIdx = (i << 6) + t;
                        break;
                    }
                }
                if (wIdx == -1) continue;
                vector<ULL> S2 = bestSet;
                bit_clear(S2, wIdx);
                bit_set(S2, u);
                auto improved = greedy_extend_from_clique(S2);
                if ((int)improved.first.size() > K) {
                    bestList = move(improved.first);
                    bestSet = move(improved.second);
                    return true;
                }
            }
        }
        return false;
    }

    vector<int> solve(double time_limit_ms = 1900.0) {
        compute_degrees();
        auto start = chrono::steady_clock::now();
        auto deadline = start + chrono::milliseconds((int)time_limit_ms);

        vector<int> bestList;
        vector<ULL> bestSet(B, 0);

        // Run initial greedy from all
        {
            auto res = greedy_from_seed(-1);
            bestList = move(res.first);
            bestSet = move(res.second);
        }

        // Seeds: top by degree
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return a < b;
        });
        int T1 = min(N, 200);
        for (int i = 0; i < T1; ++i) {
            if (chrono::steady_clock::now() > deadline) break;
            int s = order[i];
            auto res = greedy_from_seed(s);
            if ((int)res.first.size() > (int)bestList.size()) {
                bestList = move(res.first);
                bestSet = move(res.second);
            }
        }

        // Random restarts
        while (chrono::steady_clock::now() + chrono::milliseconds(50) < deadline) {
            int s = (int)(rng() % N);
            auto res = greedy_from_seed(s);
            if ((int)res.first.size() > (int)bestList.size()) {
                bestList = move(res.first);
                bestSet = move(res.second);
            }
        }

        // Local improvement via 1-swap + re-greedy
        while (chrono::steady_clock::now() + chrono::milliseconds(10) < deadline) {
            bool ok = improve_1swap_once(bestList, bestSet, deadline);
            if (!ok) break;
        }

        // Prepare output selection vector
        vector<int> select(N, 0);
        for (int v : bestList) select[v] = 1;
        return select;
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
        if (u == v) continue;
        solver.set_edge(u, v);
        solver.set_edge(v, u);
    }

    vector<int> ans = solver.solve(1900.0); // milliseconds

    for (int i = 0; i < solver.N; ++i) {
        cout << (ans[i] ? 1 : 0) << '\n';
    }
    return 0;
}