#include <bits/stdc++.h>
using namespace std;

struct MaxCliqueSolver {
    int N;
    int M;
    int W;
    vector<vector<uint64_t>> adj; // adjacency bitsets
    vector<int> deg;              // degrees
    vector<uint64_t> allMask;     // mask with N bits set to 1
    mt19937_64 rng;
    chrono::steady_clock::time_point t0;
    double time_limit_sec;

    MaxCliqueSolver(int n, int m) : N(n), M(m) {
        W = (N + 63) >> 6;
        adj.assign(N, vector<uint64_t>(W, 0));
        deg.assign(N, 0);
        allMask.assign(W, ~0ULL);
        if (N % 64) {
            allMask[W - 1] = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1);
        }
        rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());
        time_limit_sec = 1.90; // Leave some margin for I/O
        t0 = chrono::steady_clock::now();
    }

    inline bool time_up() {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        return elapsed >= time_limit_sec;
    }

    inline void set_edge(int u, int v) {
        // 0-based
        adj[u][v >> 6] |= (1ULL << (v & 63));
        adj[v][u >> 6] |= (1ULL << (u & 63));
    }

    inline bool any_bits(const vector<uint64_t>& bs) const {
        for (int i = 0; i < W; ++i) if (bs[i]) return true;
        return false;
    }

    inline int popcnt_intersection(const vector<uint64_t>& A, const vector<uint64_t>& B) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(A[i] & B[i]);
        return s;
    }

    inline int popcnt_vec(const vector<uint64_t>& A) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(A[i]);
        return s;
    }

    inline void and_assign(vector<uint64_t>& A, const vector<uint64_t>& B) const {
        for (int i = 0; i < W; ++i) A[i] &= B[i];
    }

    inline void and_not_assign(vector<uint64_t>& A, const vector<uint64_t>& B) const {
        for (int i = 0; i < W; ++i) A[i] &= ~B[i];
    }

    inline void setbit(vector<uint64_t>& A, int idx) const {
        A[idx >> 6] |= (1ULL << (idx & 63));
    }

    inline void clearbit(vector<uint64_t>& A, int idx) const {
        A[idx >> 6] &= ~(1ULL << (idx & 63));
    }

    inline bool testbit(const vector<uint64_t>& A, int idx) const {
        return (A[idx >> 6] >> (idx & 63)) & 1ULL;
    }

    int choose_vertex_from_cand(const vector<uint64_t>& cand) {
        // Choose from top-3 candidates by (neighbors within cand), breaking ties by global degree.
        int topIdx[3] = {-1, -1, -1};
        int topScore[3] = {-1, -1, -1};
        int topDeg[3] = {-1, -1, -1};

        for (int wi = 0; wi < W; ++wi) {
            uint64_t word = cand[wi];
            while (word) {
                uint64_t lsb = word & -word;
                int bit = __builtin_ctzll(word);
                int v = (wi << 6) + bit;
                if (v >= N) break;
                int score = popcnt_intersection(cand, adj[v]);
                int d = deg[v];

                // insert into top 3
                for (int pos = 0; pos < 3; ++pos) {
                    if (score > topScore[pos] || (score == topScore[pos] && d > topDeg[pos])) {
                        for (int k = 2; k > pos; --k) {
                            topScore[k] = topScore[k - 1];
                            topDeg[k] = topDeg[k - 1];
                            topIdx[k] = topIdx[k - 1];
                        }
                        topScore[pos] = score;
                        topDeg[pos] = d;
                        topIdx[pos] = v;
                        break;
                    }
                }

                word ^= lsb;
            }
        }

        int cnt = 0;
        while (cnt < 3 && topIdx[cnt] != -1) ++cnt;
        if (cnt == 0) return -1; // Shouldn't happen if cand has any bits

        uint64_t r = rng();
        if ((r % 100) < 75) return topIdx[0]; // 75% choose the best
        return topIdx[r % cnt]; // otherwise random among top-k
    }

    vector<int> greedy_expand(const vector<int>& initClique) {
        vector<int> clique = initClique;
        vector<uint64_t> Cbit(W, 0);
        for (int v : initClique) setbit(Cbit, v);

        vector<uint64_t> cand = allMask;
        for (int v : initClique) and_assign(cand, adj[v]);
        and_not_assign(cand, Cbit);

        while (any_bits(cand)) {
            if (time_up()) break;
            int v = choose_vertex_from_cand(cand);
            if (v == -1) break;
            clique.push_back(v);
            setbit(Cbit, v);
            and_assign(cand, adj[v]);
            and_not_assign(cand, Cbit);
        }
        return clique;
    }

    vector<int> improve_1swap(vector<int> clique) {
        // Try 1-1 swaps with greedy re-expansion, accept only if improvements found.
        // Loop until no improvement or time up.
        while (!time_up()) {
            vector<uint64_t> Cbit(W, 0);
            for (int v : clique) setbit(Cbit, v);

            // others = all vertices not in clique
            vector<uint64_t> others = allMask;
            and_not_assign(others, Cbit);

            bool improved = false;

            for (int wi = 0; wi < W && !improved && !time_up(); ++wi) {
                uint64_t word = others[wi];
                while (word && !improved && !time_up()) {
                    uint64_t lsb = word & -word;
                    int bit = __builtin_ctzll(word);
                    int v = (wi << 6) + bit;
                    if (v >= N) break;

                    // missing = vertices in clique that are NOT adjacent to v
                    int missingCount = 0;
                    int u_remove = -1;
                    for (int i = 0; i < W; ++i) {
                        uint64_t x = Cbit[i] & ~adj[v][i];
                        if (x) {
                            int c = __builtin_popcountll(x);
                            missingCount += c;
                            if (missingCount > 1) break;
                            // record which vertex to remove
                            int pos = (i << 6) + __builtin_ctzll(x);
                            u_remove = pos;
                        }
                    }

                    if (missingCount == 1 && u_remove >= 0) {
                        // Build new clique replacing u_remove with v
                        vector<int> newClique;
                        newClique.reserve(clique.size());
                        for (int u : clique) if (u != u_remove) newClique.push_back(u);
                        newClique.push_back(v);
                        // Re-expand greedily
                        vector<int> expanded = greedy_expand(newClique);
                        if (expanded.size() > clique.size()) {
                            clique.swap(expanded);
                            improved = true;
                            break;
                        }
                    }

                    word ^= lsb;
                }
            }

            if (!improved) break;
        }

        return clique;
    }

    vector<int> solve() {
        // compute degrees
        for (int u = 0; u < N; ++u) {
            int s = 0;
            for (int i = 0; i < W; ++i) s += __builtin_popcountll(adj[u][i]);
            deg[u] = s;
        }

        // Initial best: trivial single vertex (highest degree)
        int bestV = 0;
        for (int i = 1; i < N; ++i) if (deg[i] > deg[bestV]) bestV = i;
        vector<int> bestClique = greedy_expand(vector<int>{bestV});
        bestClique = improve_1swap(bestClique);

        // Randomized restarts until time up
        while (!time_up()) {
            // Choose starting vertex: sometimes random, sometimes best among small random sample
            int start = -1;
            if ((rng() % 100) < 60) {
                start = rng() % N;
            } else {
                int sample = 8;
                int bestd = -1;
                for (int k = 0; k < sample; ++k) {
                    int v = rng() % N;
                    if (deg[v] > bestd) { bestd = deg[v]; start = v; }
                }
                if (start == -1) start = rng() % N;
            }

            vector<int> clique = greedy_expand(vector<int>{start});
            if (time_up()) break;
            clique = improve_1swap(clique);
            if (clique.size() > bestClique.size()) {
                bestClique.swap(clique);
            }
        }

        vector<int> select(N, 0);
        for (int v : bestClique) select[v] = 1;
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
    }
    vector<int> ans = solver.solve();
    for (int i = 0; i < solver.N; ++i) {
        cout << ans[i] << "\n";
    }
    return 0;
}