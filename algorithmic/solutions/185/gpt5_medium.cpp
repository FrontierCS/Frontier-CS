#include <bits/stdc++.h>
using namespace std;

using ULL = unsigned long long;

struct FastBitset {
    int n, nb;
    vector<ULL> a;
    FastBitset() : n(0), nb(0) {}
    FastBitset(int n_) { init(n_); }
    void init(int n_) {
        n = n_;
        nb = (n + 63) >> 6;
        a.assign(nb, ~0ULL);
        if (n % 64) a.back() = (1ULL << (n % 64)) - 1ULL;
    }
    void clear() { fill(a.begin(), a.end(), 0ULL); }
    void setAll() {
        fill(a.begin(), a.end(), ~0ULL);
        if (n % 64) a.back() = (1ULL << (n % 64)) - 1ULL;
    }
    inline void set(int i) { a[i >> 6] |= (1ULL << (i & 63)); }
    inline void reset(int i) { a[i >> 6] &= ~(1ULL << (i & 63)); }
    inline bool test(int i) const { return (a[i >> 6] >> (i & 63)) & 1ULL; }
    inline bool any() const {
        for (int i = 0; i < nb; ++i) if (a[i]) return true;
        return false;
    }
    inline int popcount() const {
        int s = 0;
        for (int i = 0; i < nb; ++i) s += __builtin_popcountll(a[i]);
        return s;
    }
    inline void AND(const FastBitset &b) {
        for (int i = 0; i < nb; ++i) a[i] &= b.a[i];
    }
    inline void OR(const FastBitset &b) {
        for (int i = 0; i < nb; ++i) a[i] |= b.a[i];
    }
    inline void ANDNOT(const FastBitset &b) {
        for (int i = 0; i < nb; ++i) a[i] &= ~b.a[i];
    }
    inline int popcount_and(const FastBitset &b) const {
        int s = 0;
        for (int i = 0; i < nb; ++i) s += __builtin_popcountll(a[i] & b.a[i]);
        return s;
    }
    inline int popcount_and_not(const FastBitset &b) const {
        int s = 0;
        for (int i = 0; i < nb; ++i) s += __builtin_popcountll(a[i] & ~b.a[i]);
        return s;
    }
    inline int firstOne() const {
        for (int i = 0; i < nb; ++i) {
            ULL w = a[i];
            if (w) return (i << 6) + __builtin_ctzll(w);
        }
        return -1;
    }
    inline void toList(vector<int> &out) const {
        out.clear();
        for (int i = 0; i < nb; ++i) {
            ULL w = a[i];
            while (w) {
                int t = __builtin_ctzll(w);
                out.push_back((i << 6) + t);
                w &= (w - 1);
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    int M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    int nb = (N + 63) >> 6;
    vector<FastBitset> adj(N, FastBitset(N));
    for (int i = 0; i < N; ++i) {
        adj[i].init(N);
        adj[i].clear();
    }
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    FastBitset ALL(N);
    ALL.init(N);
    ALL.setAll();

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.95; // seconds
    auto deadline = start + chrono::duration<double>(TIME_LIMIT);

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestClique;
    FastBitset bestSet(N); bestSet.init(N); bestSet.clear();

    auto greedy_build = [&](int topK, double randPickProb, vector<int> &outClique, FastBitset &outSet) {
        outClique.clear();
        outSet.clear();
        FastBitset cand = ALL;
        // Build clique greedily
        vector<int> candList;
        uniform_real_distribution<double> dist01(0.0, 1.0);
        while (cand.any()) {
            candList.clear();
            cand.toList(candList);
            int chosen = -1;
            if (!candList.empty()) {
                if (dist01(rng) < randPickProb) {
                    uniform_int_distribution<int> d(0, (int)candList.size() - 1);
                    chosen = candList[d(rng)];
                } else {
                    // pick among topK by degree within cand
                    int k = min(topK, (int)candList.size());
                    array<int, 16> topIdx; // topK <= 16 to be safe
                    array<int, 16> topScore;
                    for (int i = 0; i < k; ++i) { topIdx[i] = -1; topScore[i] = -1; }
                    for (int v : candList) {
                        // compute degree in cand
                        int sc = adj[v].popcount_and(cand);
                        // insert into topK
                        int pos = -1;
                        for (int t = 0; t < k; ++t) {
                            if (sc > topScore[t]) { pos = t; break; }
                        }
                        if (pos != -1) {
                            for (int t = k - 1; t > pos; --t) {
                                topScore[t] = topScore[t - 1];
                                topIdx[t] = topIdx[t - 1];
                            }
                            topScore[pos] = sc;
                            topIdx[pos] = v;
                        }
                    }
                    int valid = 0;
                    while (valid < k && topIdx[valid] != -1) ++valid;
                    if (valid == 0) {
                        // fallback random
                        uniform_int_distribution<int> d(0, (int)candList.size() - 1);
                        chosen = candList[d(rng)];
                    } else {
                        uniform_int_distribution<int> d(0, valid - 1);
                        chosen = topIdx[d(rng)];
                    }
                }
            }
            if (chosen == -1) break;
            outClique.push_back(chosen);
            outSet.set(chosen);
            // intersect candidates with neighbors of chosen
            for (int i = 0; i < cand.nb; ++i) cand.a[i] &= adj[chosen].a[i];
            // chosen is not neighbor to itself (no self-loop), so it is already removed
        }
    };

    auto expand_greedy = [&](vector<int> &clique, FastBitset &clqSet, int topK) {
        FastBitset cand = ALL;
        // Intersect neighbors of all vertices in clique
        for (int v : clique) cand.AND(adj[v]);
        // Remove already in clique (not strictly necessary, but safe)
        for (int v : clique) cand.reset(v);
        vector<int> candList;
        uniform_int_distribution<int> dtop(0, max(0, topK - 1));
        while (cand.any()) {
            candList.clear();
            cand.toList(candList);
            int chosen = -1;
            // pick among topK by degree in cand
            int k = min(topK, (int)candList.size());
            array<int, 16> topIdx;
            array<int, 16> topScore;
            for (int i = 0; i < k; ++i) { topIdx[i] = -1; topScore[i] = -1; }
            for (int v : candList) {
                int sc = adj[v].popcount_and(cand);
                int pos = -1;
                for (int t = 0; t < k; ++t) {
                    if (sc > topScore[t]) { pos = t; break; }
                }
                if (pos != -1) {
                    for (int t = k - 1; t > pos; --t) {
                        topScore[t] = topScore[t - 1];
                        topIdx[t] = topIdx[t - 1];
                    }
                    topScore[pos] = sc;
                    topIdx[pos] = v;
                }
            }
            int valid = 0;
            while (valid < k && topIdx[valid] != -1) ++valid;
            if (valid == 0) {
                // pick any
                uniform_int_distribution<int> d(0, (int)candList.size() - 1);
                chosen = candList[d(rng)];
            } else {
                uniform_int_distribution<int> d(0, valid - 1);
                chosen = topIdx[d(rng)];
            }
            clique.push_back(chosen);
            clqSet.set(chosen);
            for (int i = 0; i < cand.nb; ++i) cand.a[i] &= adj[chosen].a[i];
            // chosen automatically excluded
        }
    };

    auto try_improve = [&](vector<int> &clique, FastBitset &clqSet, int topK) -> bool {
        int curSize = (int)clique.size();
        // collect candidates u not in clique with exactly one missing edge to clique
        vector<int> candU;
        FastBitset notSet = ALL;
        notSet.ANDNOT(clqSet);
        vector<int> notList;
        notSet.toList(notList);
        for (int u : notList) {
            // missing = clique \ N(u) = clqSet & ~adj[u]
            int miss = clqSet.popcount_and_not(adj[u]);
            if (miss == 1) candU.push_back(u);
        }
        if (candU.empty()) return false;
        shuffle(candU.begin(), candU.end(), rng);
        // Try candidates until find improving swap
        for (int u : candU) {
            // find the unique missing w
            FastBitset missing = clqSet;
            // missing &= ~adj[u]
            for (int i = 0; i < missing.nb; ++i) missing.a[i] &= ~adj[u].a[i];
            int w = missing.firstOne();
            if (w < 0) continue;
            // Prepare new clique
            vector<int> newClique = clique;
            // replace w with u
            bool replaced = false;
            for (int i = 0; i < (int)newClique.size(); ++i) {
                if (newClique[i] == w) { newClique[i] = u; replaced = true; break; }
            }
            if (!replaced) continue;
            FastBitset newSet = clqSet;
            newSet.reset(w);
            newSet.set(u);
            // Expand greedily
            expand_greedy(newClique, newSet, topK);
            if ((int)newClique.size() > curSize) {
                clique.swap(newClique);
                clqSet = newSet;
                return true;
            }
            // time check
            if (chrono::steady_clock::now() > deadline) break;
        }
        return false;
    };

    int topKSel = 5;
    double randPickProb = 0.08;

    // Main loop with randomized restarts
    while (chrono::steady_clock::now() < deadline) {
        vector<int> clique;
        FastBitset clqSet(N); clqSet.init(N); clqSet.clear();

        greedy_build(topKSel, randPickProb, clique, clqSet);

        // local improvements
        while (chrono::steady_clock::now() < deadline) {
            bool improved = try_improve(clique, clqSet, topKSel);
            if (!improved) break;
        }

        if ((int)clique.size() > (int)bestClique.size()) {
            bestClique = clique;
            bestSet = clqSet;
        }
        // Quick escape if we already have all vertices
        if ((int)bestClique.size() == N) break;
    }

    vector<int> out(N, 0);
    for (int v : bestClique) out[v] = 1;
    for (int i = 0; i < N; ++i) {
        cout << out[i] << '\n';
    }
    return 0;
}