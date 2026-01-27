#include <bits/stdc++.h>
using namespace std;

struct FastBitset {
    int n, W;
    vector<uint64_t> a;
    FastBitset() {}
    FastBitset(int n_) { init(n_); }
    void init(int n_) {
        n = n_;
        W = (n + 63) >> 6;
        a.assign(W, 0);
    }
    inline void set(int i) { a[i >> 6] |= (uint64_t(1) << (i & 63)); }
    inline void reset(int i) { a[i >> 6] &= ~(uint64_t(1) << (i & 63)); }
    inline bool test(int i) const { return (a[i >> 6] >> (i & 63)) & 1ULL; }
    inline void setAll() {
        std::fill(a.begin(), a.end(), ~0ULL);
        int extra = (W << 6) - n;
        if (extra) a[W - 1] >>= extra, a[W - 1] <<= extra, a[W - 1] |= ((1ULL << (64 - extra)) - 1ULL);
    }
    inline void clearAll() { std::fill(a.begin(), a.end(), 0ULL); }
    inline void assign(const FastBitset &o) { a = o.a; }
    inline void AND(const FastBitset &o) {
        for (int i = 0; i < W; ++i) a[i] &= o.a[i];
    }
    inline int popcount() const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i]);
        return s;
    }
    inline int popcount_and(const FastBitset &o) const {
        int s = 0;
        for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i] & o.a[i]);
        return s;
    }
    // Iterate set bits and call fn(index)
    template <class F>
    inline void for_each_set(F fn) const {
        for (int i = 0; i < W; ++i) {
            uint64_t x = a[i];
            while (x) {
                int b = __builtin_ctzll(x);
                int idx = (i << 6) + b;
                if (idx < n) fn(idx);
                x &= x - 1;
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<FastBitset> adj(N, FastBitset(N));
    for (int i = 0; i < N; ++i) adj[i].init(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!adj[u].test(v)) {
            adj[u].set(v);
            adj[v].set(u);
            deg[u]++; deg[v]++;
        }
    }

    auto start_time = chrono::steady_clock::now();
    auto time_limit = chrono::milliseconds(1800);

    vector<int> best_clique;
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    // Greedy-by-order heuristic
    {
        FastBitset cand(N);
        cand.setAll();
        vector<int> clique;
        for (int v: order) {
            if (cand.test(v)) {
                clique.push_back(v);
                cand.AND(adj[v]);
            }
        }
        best_clique = clique;
    }

    std::mt19937 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto expand_from_seed = [&](int seed) -> vector<int> {
        vector<int> clique;
        clique.reserve(N);
        clique.push_back(seed);
        FastBitset cand(N);
        cand.assign(adj[seed]);
        while (true) {
            int best_v = -1;
            int best_score = -1;
            // Select vertex in cand with maximum connections within cand
            cand.for_each_set([&](int v){
                int s = adj[v].popcount_and(cand);
                // tiny random tie-break
                int jitter = rng() & 1;
                int score = (s << 1) + jitter;
                if (score > best_score) {
                    best_score = score;
                    best_v = v;
                }
            });
            if (best_v == -1) break;
            clique.push_back(best_v);
            cand.AND(adj[best_v]);
        }
        return clique;
    };

    // Prepare seeds: top by degree and some random picks
    vector<int> seeds;
    int topk = min(N, 200);
    for (int i = 0; i < topk; ++i) seeds.push_back(order[i]);
    // add random unique seeds
    uniform_int_distribution<int> dist(0, N - 1);
    while ((int)seeds.size() < min(N, 400)) {
        int v = dist(rng);
        seeds.push_back(v);
    }
    // also add vertices with highest degrees interleaved
    for (int i = topk; i < N && (int)seeds.size() < 600; ++i) seeds.push_back(order[i]);

    // Shuffle to diversify runs
    shuffle(seeds.begin(), seeds.end(), rng);

    for (int sidx = 0; sidx < (int)seeds.size(); ++sidx) {
        if (chrono::steady_clock::now() - start_time > time_limit) break;
        int seed = seeds[sidx];
        auto clique = expand_from_seed(seed);
        if (clique.size() > best_clique.size()) best_clique = move(clique);
    }

    // Additional randomized order-based tries within time
    while (chrono::steady_clock::now() - start_time < time_limit) {
        vector<pair<int,int>> weighted(N);
        for (int i = 0; i < N; ++i) {
            int noise = rng() % (N + 1);
            weighted[i] = {deg[i] * 4 + noise, i};
        }
        sort(weighted.begin(), weighted.end(), [&](auto &A, auto &B){
            if (A.first != B.first) return A.first > B.first;
            return A.second < B.second;
        });
        FastBitset cand(N);
        cand.setAll();
        vector<int> clique;
        for (auto &p : weighted) {
            int v = p.second;
            if (cand.test(v)) {
                clique.push_back(v);
                cand.AND(adj[v]);
            }
        }
        if (clique.size() > best_clique.size()) best_clique = move(clique);
    }

    vector<char> in_clique(N, 0);
    for (int v : best_clique) in_clique[v] = 1;
    for (int i = 0; i < N; ++i) {
        cout << (in_clique[i] ? 1 : 0) << '\n';
    }
    return 0;
}