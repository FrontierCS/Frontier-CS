#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

static inline int popcount64(ull x) { return __builtin_popcountll(x); }

struct Graph {
    int N, M;
    int W; // number of 64-bit words
    ull LAST_MASK; // mask for the last word
    vector<vector<ull>> adj; // adjacency bitsets
    vector<int> deg;
    mt19937_64 rng;

    Graph(int n=0): N(n), M(0) {
        if (N > 0) init(N);
    }

    void init(int n) {
        N = n;
        W = (N + 63) >> 6;
        int rem = N & 63;
        LAST_MASK = (rem == 0) ? ~0ULL : ((1ULL << rem) - 1ULL);
        adj.assign(N, vector<ull>(W, 0));
        deg.assign(N, 0);
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    inline void setbit(vector<ull>& b, int pos) {
        b[pos >> 6] |= (1ULL << (pos & 63));
    }
    inline void resetbit(vector<ull>& b, int pos) {
        b[pos >> 6] &= ~(1ULL << (pos & 63));
    }
    inline bool testbit(const vector<ull>& b, int pos) const {
        return (b[pos >> 6] >> (pos & 63)) & 1ULL;
    }
    inline void fill_all(vector<ull>& b) const {
        for (int i = 0; i < W; ++i) b[i] = ~0ULL;
        b[W-1] &= LAST_MASK;
    }
    inline void clear_all(vector<ull>& b) const {
        for (int i = 0; i < W; ++i) b[i] = 0ULL;
    }
    inline bool any_bits(const vector<ull>& b) const {
        for (int i = 0; i < W; ++i) if (b[i]) return true;
        return false;
    }
    inline int count_bits(const vector<ull>& b) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += popcount64(b[i]);
        return s;
    }
    inline int count_and(const vector<ull>& a, const vector<ull>& b) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += popcount64(a[i] & b[i]);
        return s;
    }
    inline void and_assign(vector<ull>& a, const vector<ull>& b) const {
        for (int i = 0; i < W; ++i) a[i] &= b[i];
    }
    inline void or_assign(vector<ull>& a, const vector<ull>& b) const {
        for (int i = 0; i < W; ++i) a[i] |= b[i];
    }
    inline void and_not_assign(vector<ull>& a, const vector<ull>& b) const {
        for (int i = 0; i < W; ++i) a[i] &= ~b[i];
    }
    inline void assign_and(vector<ull>& out, const vector<ull>& a, const vector<ull>& b) const {
        for (int i = 0; i < W; ++i) out[i] = a[i] & b[i];
    }
    inline void assign_copy(vector<ull>& out, const vector<ull>& a) const {
        for (int i = 0; i < W; ++i) out[i] = a[i];
    }

    inline void enumerate_bits(const vector<ull>& b, vector<int>& out) const {
        out.clear();
        for (int i = 0; i < W; ++i) {
            ull x = b[i];
            while (x) {
                ull t = x & -x;
                int r = __builtin_ctzll(x);
                int pos = (i << 6) + r;
                if (pos < N) out.push_back(pos);
                x ^= t;
            }
        }
    }

    void add_edge(int u, int v) {
        if ((int)adj.size() == 0) return;
        if (u == v) return;
        setbit(adj[u], v);
        setbit(adj[v], u);
    }

    void finalize_degrees() {
        for (int i = 0; i < N; ++i) {
            deg[i] = count_bits(adj[i]);
        }
    }

    // Select a vertex from candidate set by choosing randomly among top L by (neighbors within cand)
    int select_from_cand_topL(const vector<ull>& cand, int topL) {
        struct Cand { int idx; int score; int deg; };
        vector<Cand> best;
        best.reserve(topL);
        // Enumerate candidates
        for (int i = 0; i < N; ++i) {
            if (!testbit(cand, i)) continue;
            int s = count_and(adj[i], cand);
            Cand c{ i, s, deg[i] };
            if ((int)best.size() < topL) {
                best.push_back(c);
                // insertion sort small
                for (int j = (int)best.size()-1; j > 0; --j) {
                    if (best[j].score > best[j-1].score || (best[j].score == best[j-1].score && best[j].deg > best[j-1].deg))
                        swap(best[j], best[j-1]);
                    else break;
                }
            } else {
                // compare with smallest (last)
                int j = topL - 1;
                if (c.score > best[j].score || (c.score == best[j].score && c.deg > best[j].deg)) {
                    best[j] = c;
                    // bubble up
                    while (j > 0 && (best[j].score > best[j-1].score || (best[j].score == best[j-1].score && best[j].deg > best[j-1].deg))) {
                        swap(best[j], best[j-1]);
                        --j;
                    }
                }
            }
        }
        if (best.empty()) return -1;
        uniform_int_distribution<int> dist(0, (int)best.size()-1);
        int pick = dist(rng);
        return best[pick].idx;
    }

    void greedy_expand_within(vector<int>& clique, vector<ull>& cand, int topL) {
        while (any_bits(cand)) {
            int v = select_from_cand_topL(cand, topL);
            if (v == -1) break;
            clique.push_back(v);
            and_assign(cand, adj[v]);
        }
    }

    vector<int> greedy_randomized_clique(int topL) {
        vector<int> clique;
        vector<ull> cand(W);
        fill_all(cand);
        // Build clique using greedy randomized selection
        while (any_bits(cand)) {
            int v = select_from_cand_topL(cand, topL);
            if (v == -1) break;
            clique.push_back(v);
            and_assign(cand, adj[v]);
        }
        return clique;
    }

    bool one_swap_improvement(vector<int>& clique, int topLExpand) {
        int K = (int)clique.size();
        if (K <= 0) return false;

        // Build clique bitset B and position map
        vector<ull> B(W, 0ULL);
        vector<int> posInClique(N, -1);
        for (int i = 0; i < K; ++i) {
            setbit(B, clique[i]);
            posInClique[clique[i]] = i;
        }

        // Prefix and suffix intersections of adjacencies
        vector<vector<ull>> pref(K + 1, vector<ull>(W, 0ULL)), suff(K + 1, vector<ull>(W, 0ULL));
        fill_all(pref[0]);
        for (int i = 0; i < K; ++i) {
            assign_and(pref[i+1], pref[i], adj[clique[i]]);
        }
        fill_all(suff[K]);
        for (int i = K-1; i >= 0; --i) {
            assign_and(suff[i], suff[i+1], adj[clique[i]]);
        }

        // c_excl[i] = intersection of adj for clique except i
        vector<vector<ull>> c_excl(K, vector<ull>(W, 0ULL));
        for (int i = 0; i < K; ++i) {
            assign_and(c_excl[i], pref[i], suff[i+1]);
        }

        int bestW = -1;
        int bestUIdx = -1;
        int bestScore = 0;
        int bestDeg = -1;

        // Scan all nodes outside clique to see if they miss exactly one adjacency to the clique
        for (int w = 0; w < N; ++w) {
            if (posInClique[w] != -1) continue;
            // Compute which clique vertices are not adjacent to w: missing = B & ~adj[w]
            int missingCount = 0;
            int missingVertex = -1; // vertex id
            for (int i = 0; i < W; ++i) {
                ull m = B[i] & ~adj[w][i];
                if (m) {
                    missingCount += popcount64(m);
                    if (missingCount > 1) break;
                    // find which bit
                    int r = __builtin_ctzll(m);
                    missingVertex = (i << 6) + r;
                }
            }
            if (missingCount != 1) continue;
            if (missingVertex < 0 || missingVertex >= N) continue;
            int uIdx = posInClique[missingVertex];
            if (uIdx < 0) continue;

            // score: potential candidate set size after swap = |c_excl[uIdx] ∩ adj[w]|
            int sc = count_and(c_excl[uIdx], adj[w]);
            if (sc > bestScore || (sc == bestScore && deg[w] > bestDeg)) {
                bestScore = sc;
                bestW = w;
                bestUIdx = uIdx;
                bestDeg = deg[w];
            }
        }

        if (bestScore >= 1 && bestW != -1 && bestUIdx != -1) {
            // Apply swap: remove u, add w, then expand greedily from cand = c_excl[u] ∩ adj[w]
            int uVertex = clique[bestUIdx];
            // Update clique vector: replace position bestUIdx with bestW
            clique[bestUIdx] = bestW;

            // Build candidate set for expansion
            vector<ull> cand(W, 0ULL);
            assign_and(cand, c_excl[bestUIdx], adj[bestW]);

            // Note: cand excludes current clique nodes inherently because c_excl excludes them, but ensure w is also excluded:
            // adj[w] doesn't include w, so fine.

            // Greedily expand within cand
            greedy_expand_within(clique, cand, topLExpand);
            return true;
        }
        return false;
    }

    void local_search(vector<int>& clique) {
        // Iteratively apply 1-swap improvements until none applies
        // Use small topL for expansion
        const int topLExpand = 4;
        while (one_swap_improvement(clique, topLExpand)) {
            // continue improving
        }
    }

    bool verify_clique(const vector<int>& clique) const {
        int k = (int)clique.size();
        for (int i = 0; i < k; ++i) {
            int u = clique[i];
            for (int j = i + 1; j < k; ++j) {
                int v = clique[j];
                if (!testbit(adj[u], v)) return false;
            }
        }
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    Graph G(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u >= 0 && u < N && v >= 0 && v < N && u != v) {
            G.add_edge(u, v);
        }
    }
    G.finalize_degrees();

    // Time limit control
    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.90; // seconds; a bit under 2s

    vector<int> best_clique;
    int best_size = 0;

    // Initial deterministic greedy
    {
        vector<int> c0 = G.greedy_randomized_clique(1); // deterministic greedy
        G.local_search(c0);
        if ((int)c0.size() > best_size) {
            best_size = (int)c0.size();
            best_clique = c0;
        }
    }

    // Multi-start randomized greedy + local search until time is up
    int iter = 0;
    while (true) {
        auto t_now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(t_now - t_start).count();
        if (elapsed > TIME_LIMIT) break;

        int topL = 3 + (iter % 3); // vary between 3,4,5
        vector<int> clique = G.greedy_randomized_clique(topL);
        G.local_search(clique);

        if ((int)clique.size() > best_size) {
            best_size = (int)clique.size();
            best_clique = clique;
        }
        ++iter;
    }

    // Build selection vector
    vector<int> inClique(N, 0);
    for (int v : best_clique) {
        if (v >= 0 && v < N) inClique[v] = 1;
    }

    // Output exactly N lines with 0/1
    for (int i = 0; i < N; ++i) {
        cout << (inClique[i] ? 1 : 0) << '\n';
    }

    return 0;
}