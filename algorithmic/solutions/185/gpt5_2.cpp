#include <bits/stdc++.h>
using namespace std;

struct FastBitset {
    int n;
    int w;
    uint64_t lastMask;
    vector<uint64_t> d;

    FastBitset() : n(0), w(0), lastMask(0) {}
    FastBitset(int n_) { init(n_); }

    void init(int n_) {
        n = n_;
        w = (n + 63) >> 6;
        d.assign(w, 0);
        int r = n & 63;
        lastMask = (r == 0) ? ~0ULL : ((1ULL << r) - 1);
    }

    inline void clear() {
        std::fill(d.begin(), d.end(), 0ULL);
    }
    inline void setAll() {
        std::fill(d.begin(), d.end(), ~0ULL);
        if (w) d[w-1] &= lastMask;
    }
    inline void set(int i) {
        d[i >> 6] |= (1ULL << (i & 63));
    }
    inline void reset(int i) {
        d[i >> 6] &= ~(1ULL << (i & 63));
    }
    inline bool test(int i) const {
        return (d[i >> 6] >> (i & 63)) & 1ULL;
    }
    inline int count() const {
        int s = 0;
        for (int i = 0; i < w; ++i) s += __builtin_popcountll(d[i]);
        return s;
    }
    inline int count_and(const FastBitset& b) const {
        int s = 0;
        for (int i = 0; i < w; ++i) s += __builtin_popcountll(d[i] & b.d[i]);
        return s;
    }
    inline int count_andnot(const FastBitset& b) const {
        int s = 0;
        for (int i = 0; i < w; ++i) {
            uint64_t x = d[i] & ~b.d[i];
            if (i == w - 1) x &= lastMask;
            s += __builtin_popcountll(x);
        }
        return s;
    }
    inline bool any() const {
        for (int i = 0; i < w; ++i) if (d[i]) return true;
        return false;
    }
    inline void AND(const FastBitset& b) {
        for (int i = 0; i < w; ++i) d[i] &= b.d[i];
    }
    inline void OR(const FastBitset& b) {
        for (int i = 0; i < w; ++i) d[i] |= b.d[i];
        if (w) d[w-1] &= lastMask;
    }
    inline void ANDNOT(const FastBitset& b) {
        for (int i = 0; i < w; ++i) d[i] &= ~b.d[i];
        if (w) d[w-1] &= lastMask;
    }
    inline void NOT_INPLACE() {
        for (int i = 0; i < w; ++i) d[i] = ~d[i];
        if (w) d[w-1] &= lastMask;
    }
    inline FastBitset NOT() const {
        FastBitset r = *this;
        r.NOT_INPLACE();
        return r;
    }

    inline void toVector(vector<int>& out) const {
        out.clear();
        out.reserve(count());
        for (int i = 0; i < w; ++i) {
            uint64_t x = d[i];
            while (x) {
                uint64_t lsb = x & -x;
                int b = __builtin_ctzll(x);
                out.push_back((i << 6) + b);
                x ^= lsb;
            }
        }
    }

    inline int firstOne() const {
        for (int i = 0; i < w; ++i) {
            if (d[i]) return (i << 6) + __builtin_ctzll(d[i]);
        }
        return -1;
    }
};

struct CliqueSolver {
    int N, M;
    vector<FastBitset> adj;
    vector<int> deg;
    FastBitset universe;
    mt19937_64 rng;
    chrono::steady_clock::time_point startTime;
    double timeLimitSec;

    CliqueSolver(int n, int m) : N(n), M(m), adj(n, FastBitset(n)), deg(n, 0), universe(n) {
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
        startTime = chrono::steady_clock::now();
        timeLimitSec = 1.95;
        universe.setAll();
    }

    inline bool timeUp() const {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        return elapsed >= timeLimitSec;
    }

    void add_edge(int u, int v) {
        if (u == v) return;
        adj[u].set(v);
        adj[v].set(u);
    }

    int score_in_set(int v, const FastBitset& C) const {
        int s = 0;
        for (int i = 0; i < C.w; ++i) s += __builtin_popcountll(adj[v].d[i] & C.d[i]);
        return s;
    }

    void maximalize(FastBitset& R) {
        // Compute candidate set as intersection of neighbors of current clique
        FastBitset C(N);
        C.setAll();
        vector<int> Rlist;
        R.toVector(Rlist);
        for (int v : Rlist) C.AND(adj[v]);
        // Exclude already in R
        FastBitset Rnot = R.NOT();
        C.AND(Rnot);

        vector<int> candList;
        candList.reserve(N);
        while (C.any()) {
            C.toVector(candList);
            int bestv = -1, bestscore = -1;
            for (int v : candList) {
                int sc = score_in_set(v, C);
                if (sc > bestscore) {
                    bestscore = sc;
                    bestv = v;
                }
            }
            if (bestv == -1) break;
            R.set(bestv);
            C.AND(adj[bestv]);
            // exclude already in R automatically due to no self-loop, but to be safe:
            if (C.test(bestv)) C.reset(bestv);
            if (timeUp()) break;
        }
    }

    FastBitset greedy_randomized(int topK_base) {
        FastBitset R(N), C(N);
        R.clear();
        C.setAll();
        vector<int> candList;
        vector<pair<int,int>> scored; // (score, v)

        while (C.any()) {
            if (timeUp()) break;
            candList.clear();
            C.toVector(candList);
            scored.clear();
            scored.reserve(candList.size());
            for (int v : candList) {
                int sc = score_in_set(v, C);
                scored.emplace_back(sc, v);
            }
            sort(scored.begin(), scored.end(), [](const auto& a, const auto& b){
                if (a.first != b.first) return a.first > b.first;
                return a.second < b.second;
            });
            int K = min<int>((int)scored.size(), topK_base);
            uniform_int_distribution<int> dist(0, K - 1);
            int pick = dist(rng);
            int v = scored[pick].second;

            R.set(v);
            C.AND(adj[v]);
            if (C.test(v)) C.reset(v);
        }
        return R;
    }

    bool improve_1swap(FastBitset& R) {
        int prev_size = R.count();
        FastBitset outside = universe;
        outside.ANDNOT(R);
        vector<int> outList;
        outside.toVector(outList);
        // Shuffle to add randomness and avoid worst-case ordering
        shuffle(outList.begin(), outList.end(), rng);

        FastBitset missing(N);
        for (int w : outList) {
            if (timeUp()) return false;
            // Compute missing = R & ~N(w)
            missing = R;
            missing.ANDNOT(adj[w]);
            int misscnt = missing.count();
            if (misscnt == 0) {
                FastBitset newR = R;
                newR.set(w);
                maximalize(newR);
                if (newR.count() > prev_size) {
                    R = newR;
                    return true;
                }
            } else if (misscnt == 1) {
                int u = missing.firstOne();
                FastBitset newR = R;
                newR.reset(u);
                newR.set(w);
                maximalize(newR);
                if (newR.count() > prev_size) {
                    R = newR;
                    return true;
                }
            }
        }
        return false;
    }

    vector<int> solve() {
        // Prepare degrees
        for (int i = 0; i < N; ++i) deg[i] = adj[i].count();

        FastBitset best(N);
        int bestSize = 0;

        // Deterministic greedy as baseline
        {
            FastBitset R = greedy_randomized(1);
            maximalize(R);
            if (R.count() > bestSize) {
                best = R;
                bestSize = R.count();
            }
        }

        // Main randomized GRASP-like loop
        int iteration = 0;
        while (!timeUp()) {
            int topK = 1 + (int)(rng() % 8); // choose topK in [1..8]
            FastBitset R = greedy_randomized(topK);
            maximalize(R);
            // Local improvement with 1-swap
            while (!timeUp()) {
                bool imp = improve_1swap(R);
                if (!imp) break;
            }
            int sz = R.count();
            if (sz > bestSize) {
                best = R;
                bestSize = sz;
            }
            iteration++;
        }

        // Convert best to output vector
        vector<int> ans(N, 0);
        for (int i = 0; i < N; ++i) if (best.test(i)) ans[i] = 1;
        return ans;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    CliqueSolver solver(N, M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u >= 0 && u < N && v >= 0 && v < N && u != v) {
            solver.add_edge(u, v);
        }
    }
    vector<int> ans = solver.solve();
    for (int i = 0; i < N; ++i) {
        cout << ans[i] << "\n";
    }
    return 0;
}