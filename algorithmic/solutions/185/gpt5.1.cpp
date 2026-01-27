#include <bits/stdc++.h>
using namespace std;

struct FastBitset {
    static const int MAXN = 1000;
    static const int WORDS = (MAXN + 63) / 64;
    uint64_t w[WORDS];

    FastBitset() { reset(); }

    inline void reset() { memset(w, 0, sizeof(w)); }

    inline void set(int pos) { w[pos >> 6] |= 1ULL << (pos & 63); }

    inline bool test(int pos) const { return (w[pos >> 6] >> (pos & 63)) & 1ULL; }

    inline bool any() const {
        for (int i = 0; i < WORDS; ++i)
            if (w[i]) return true;
        return false;
    }

    inline int count() const {
        int r = 0;
        for (int i = 0; i < WORDS; ++i)
            r += __builtin_popcountll(w[i]);
        return r;
    }

    inline int next(int pos) const {
        int word = pos >> 6;
        int bit = pos & 63;
        if (word >= WORDS) return -1;
        uint64_t cur = w[word] & (~0ULL << bit);
        while (true) {
            if (cur) return (word << 6) + __builtin_ctzll(cur);
            ++word;
            if (word >= WORDS) return -1;
            cur = w[word];
        }
    }

    inline FastBitset &operator&=(const FastBitset &o) {
        for (int i = 0; i < WORDS; ++i) w[i] &= o.w[i];
        return *this;
    }
};

int N, M;
vector<FastBitset> adj;
vector<int> deg;
mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
chrono::steady_clock::time_point startTime;
const double TIME_LIMIT = 1.9;
int globalUpperBound;

void greedyFromSeed(int seed, bool randomized, vector<int> &bestClique, int &bestSize) {
    vector<int> clique;
    clique.reserve(N);
    clique.push_back(seed);

    FastBitset cand = adj[seed];
    int candCount = cand.count();

    while (candCount > 0) {
        if (chrono::duration<double>(chrono::steady_clock::now() - startTime).count() > TIME_LIMIT)
            return;

        if ((int)clique.size() + candCount <= bestSize) break;

        int bestv = -1;
        int bestScore = -1;

        if (!randomized) {
            for (int v = cand.next(0); v != -1; v = cand.next(v + 1)) {
                int s = deg[v];
                if (s > bestScore) {
                    bestScore = s;
                    bestv = v;
                }
            }
        } else {
            for (int v = cand.next(0); v != -1; v = cand.next(v + 1)) {
                int s = (deg[v] << 10) + int(rng() & 1023ULL);
                if (s > bestScore) {
                    bestScore = s;
                    bestv = v;
                }
            }
        }

        if (bestv == -1) break;

        clique.push_back(bestv);
        cand &= adj[bestv];
        candCount = cand.count();
    }

    if ((int)clique.size() > bestSize) {
        bestSize = (int)clique.size();
        bestClique = clique;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;

    adj.assign(N, FastBitset());

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    deg.assign(N, 0);
    int maxDeg = 0;
    for (int i = 0; i < N; ++i) {
        deg[i] = adj[i].count();
        if (deg[i] > maxDeg) maxDeg = deg[i];
    }
    globalUpperBound = maxDeg + 1;

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return deg[a] > deg[b];
    });

    vector<int> bestClique;
    int bestSize = 0;

    startTime = chrono::steady_clock::now();

    // Deterministic phase: high-degree seeds
    for (int idx = 0; idx < N; ++idx) {
        if (bestSize == globalUpperBound) break;
        if (chrono::duration<double>(chrono::steady_clock::now() - startTime).count() > TIME_LIMIT)
            break;
        int v = order[idx];
        if (deg[v] + 1 <= bestSize) break;
        greedyFromSeed(v, false, bestClique, bestSize);
    }

    // Randomized phase: random seeds with noisy selection
    while (bestSize < globalUpperBound &&
           chrono::duration<double>(chrono::steady_clock::now() - startTime).count() <= TIME_LIMIT) {
        int seed = (int)(rng() % N);
        greedyFromSeed(seed, true, bestClique, bestSize);
        if (bestSize == globalUpperBound) break;
    }

    vector<int> ans(N, 0);
    for (int v : bestClique) {
        if (v >= 0 && v < N) ans[v] = 1;
    }

    for (int i = 0; i < N; ++i) {
        cout << ans[i] << '\n';
    }

    return 0;
}