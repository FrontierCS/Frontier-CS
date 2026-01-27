#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    int L = (n + 63) >> 6;

    auto idx = [L](int r, int c) -> size_t { return (size_t)r * L + (c >> 6); };
    auto maskbit = [](int c) -> uint64_t { return 1ULL << (c & 63); };

    vector<vector<int>> g1(n), g2(n);
    vector<uint64_t> A1((size_t)n * L, 0), A2((size_t)n * L, 0);

    auto set_edge = [&](vector<uint64_t>& A, int u, int v){
        A[idx(u, v)] |= maskbit(v);
        A[idx(v, u)] |= maskbit(u);
    };

    for (long long i = 0; i < m; i++) {
        int u, v; cin >> u >> v; --u; --v;
        g1[u].push_back(v); g1[v].push_back(u);
        set_edge(A1, u, v);
    }
    for (long long i = 0; i < m; i++) {
        int u, v; cin >> u >> v; --u; --v;
        g2[u].push_back(v); g2[v].push_back(u);
        set_edge(A2, u, v);
    }

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; i++) {
        deg1[i] = (int)g1[i].size();
        deg2[i] = (int)g2[i].size();
    }

    // Degree compression for initial colors
    vector<int> degVals;
    degVals.reserve(2u * n);
    for (int i = 0; i < n; i++) degVals.push_back(deg1[i]);
    for (int i = 0; i < n; i++) degVals.push_back(deg2[i]);
    sort(degVals.begin(), degVals.end());
    degVals.erase(unique(degVals.begin(), degVals.end()), degVals.end());
    vector<int> deg2id(n+1, -1);
    for (int i = 0; i < (int)degVals.size(); i++) {
        if (degVals[i] <= n) deg2id[degVals[i]] = i;
    }

    vector<int> col1(n), col2(n);
    for (int i = 0; i < n; i++) col1[i] = deg2id[deg1[i]];
    for (int i = 0; i < n; i++) col2[i] = deg2id[deg2[i]];
    int colorCount = (int)degVals.size();

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    vector<uint64_t> R1(max(2*colorCount, 4)), R2(max(2*colorCount, 4));
    for (int i = 0; i < (int)R1.size(); i++) { R1[i] = splitmix64(seed); R2[i] = splitmix64(seed); }

    auto ensureRandom = [&](int need){
        if (need <= (int)R1.size()) return;
        int old = (int)R1.size();
        R1.resize(need);
        R2.resize(need);
        for (int i = old; i < need; i++) { R1[i] = splitmix64(seed); R2[i] = splitmix64(seed); }
    };

    // WL refinement (2 iterations)
    int WL_ITERS = 2;
    vector<uint64_t> s1_1(n), s2_1(n), s1_2(n), s2_2(n);
    for (int it = 0; it < WL_ITERS; it++) {
        ensureRandom(colorCount + 5);
        // Graph 1
        for (int i = 0; i < n; i++) {
            uint64_t a = R1[col1[i]];
            uint64_t b = R2[col1[i]];
            a += (uint64_t)deg1[i] * 1000003ULL;
            b ^= (uint64_t)deg1[i] * 0x9e3779b97f4a7c15ULL;
            for (int v : g1[i]) {
                a += R1[col1[v]];
                b ^= (R2[col1[v]] + 0x517cc1b727220a95ULL);
            }
            s1_1[i] = a; s2_1[i] = b;
        }
        // Graph 2
        for (int i = 0; i < n; i++) {
            uint64_t a = R1[col2[i]];
            uint64_t b = R2[col2[i]];
            a += (uint64_t)deg2[i] * 1000003ULL;
            b ^= (uint64_t)deg2[i] * 0x9e3779b97f4a7c15ULL;
            for (int v : g2[i]) {
                a += R1[col2[v]];
                b ^= (R2[col2[v]] + 0x517cc1b727220a95ULL);
            }
            s1_2[i] = a; s2_2[i] = b;
        }

        struct Key { uint64_t a, b; int c; int t, idx; };
        vector<Key> all;
        all.reserve(2u * n);
        for (int i = 0; i < n; i++) all.push_back({s1_1[i], s2_1[i], col1[i], 0, i});
        for (int i = 0; i < n; i++) all.push_back({s1_2[i], s2_2[i], col2[i], 1, i});
        sort(all.begin(), all.end(), [](const Key& x, const Key& y){
            if (x.c != y.c) return x.c < y.c;
            if (x.a != y.a) return x.a < y.a;
            if (x.b != y.b) return x.b < y.b;
            if (x.t != y.t) return x.t < y.t;
            return x.idx < y.idx;
        });
        int newColorCount = 0;
        auto sameKey = [](const Key& x, const Key& y){
            return x.c == y.c && x.a == y.a && x.b == y.b;
        };
        vector<int> newCol1(n), newCol2(n);
        for (size_t i = 0; i < all.size(); ) {
            size_t j = i + 1;
            while (j < all.size() && sameKey(all[i], all[j])) j++;
            for (size_t k = i; k < j; k++) {
                if (all[k].t == 0) newCol1[all[k].idx] = newColorCount;
                else newCol2[all[k].idx] = newColorCount;
            }
            newColorCount++;
            i = j;
        }
        col1.swap(newCol1);
        col2.swap(newCol2);
        ensureRandom(newColorCount + 5);
        // If stable, we could break early but keep fixed iterations for simplicity
        colorCount = newColorCount;
    }

    // Initial mapping: sort by (color, degree, s1, s2)
    vector<int> ord1(n), ord2(n);
    iota(ord1.begin(), ord1.end(), 0);
    iota(ord2.begin(), ord2.end(), 0);
    sort(ord1.begin(), ord1.end(), [&](int a, int b){
        if (col1[a] != col1[b]) return col1[a] < col1[b];
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        if (s1_1[a] != s1_1[b]) return s1_1[a] < s1_1[b];
        if (s2_1[a] != s2_1[b]) return s2_1[a] < s2_1[b];
        return a < b;
    });
    sort(ord2.begin(), ord2.end(), [&](int a, int b){
        if (col2[a] != col2[b]) return col2[a] < col2[b];
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        if (s1_2[a] != s1_2[b]) return s1_2[a] < s1_2[b];
        if (s2_2[a] != s2_2[b]) return s2_2[a] < s2_2[b];
        return a < b;
    });

    vector<int> p(n), invp(n);
    for (int i = 0; i < n; i++) {
        p[ord2[i]] = ord1[i];
    }
    for (int i = 0; i < n; i++) invp[p[i]] = i;

    // Build Q bitsets: for each u in G2, Q[u][p[v]] = 1 for v in N2(u)
    vector<uint64_t> Q((size_t)n * L, 0);
    auto bit_get = [&](const vector<uint64_t>& A, int r, int c)->int {
        return (int)((A[idx(r, c)] >> (c & 63)) & 1ULL);
    };
    auto bit_assign = [&](vector<uint64_t>& A, int r, int c, bool val){
        size_t id = idx(r, c);
        uint64_t msk = maskbit(c);
        if (val) A[id] |= msk;
        else A[id] &= ~msk;
    };
    auto rowptr = [&](vector<uint64_t>& A, int r)->uint64_t* { return &A[(size_t)r * L]; };
    auto rowptrc = [&](const vector<uint64_t>& A, int r)->const uint64_t* { return &A[(size_t)r * L]; };
    for (int u = 0; u < n; u++) {
        uint64_t* Qu = rowptr(Q, u);
        (void)Qu;
        for (int v : g2[u]) {
            int j = p[v];
            Q[idx(u, j)] |= maskbit(j);
        }
    }

    auto popcount_and = [&](const uint64_t* a, const uint64_t* b)->int {
        int s = 0;
        for (int k = 0; k < L; k++) s += __builtin_popcountll(a[k] & b[k]);
        return s;
    };

    // Compute S[u] = number of matched edges incident to u (double-counted)
    vector<int> S(n, 0);
    long long matched_dbl = 0;
    for (int u = 0; u < n; u++) {
        S[u] = popcount_and(rowptrc(A1, p[u]), rowptrc(Q, u));
        matched_dbl += S[u];
    }

    // Improvement: local search with time limit
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_MS = 1800.0;

    // Helper: update pool of "bad" vertices
    vector<int> pool;
    auto update_pool = [&](){
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b){
            int ba = deg2[a] - S[a]; // unmatched incident edges around a
            int bb = deg2[b] - S[b];
            if (ba != bb) return ba > bb;
            if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
            return a < b;
        });
        int K = max(16, min(n, 512));
        pool.assign(ord.begin(), ord.begin() + K);
    };
    update_pool();

    auto elapsed_ms = [&](){
        return chrono::duration<double, std::milli>(chrono::steady_clock::now() - start).count();
    };

    // Random generator
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    int iter = 0;
    while (elapsed_ms() < TIME_LIMIT_MS) {
        if ((iter & 511) == 0) update_pool();
        iter++;

        int x = pool[rng() % pool.size()];
        int a = p[x];

        // find best target j for x maximizing overlap with Q[x]
        const uint64_t* Qx = rowptrc(Q, x);
        int bestJ = -1, bestVal = -1, secondJ = -1, secondVal = -1;
        for (int j = 0; j < n; j++) {
            int val = popcount_and(rowptrc(A1, j), Qx);
            if (val > bestVal) {
                secondVal = bestVal; secondJ = bestJ;
                bestVal = val; bestJ = j;
            } else if (val > secondVal) {
                secondVal = val; secondJ = j;
            }
        }
        int y = invp[bestJ];
        if (y == x) {
            if (secondJ >= 0) y = invp[secondJ];
            if (y == x) {
                // fallback random y
                do { y = (int)(rng() % n); } while (y == x);
            }
        }
        int b = p[y];

        // Compute delta if swapping x and y
        int Sx_old = S[x], Sy_old = S[y];

        int xyEdge = bit_get(A2, x, y);
        int syxEdge = xyEdge; // symmetrical

        int Sx_new = popcount_and(rowptrc(A1, b), Qx) + (xyEdge ? bit_get(A1, b, a) : 0);

        const uint64_t* Qy = rowptrc(Q, y);
        int Sy_new = popcount_and(rowptrc(A1, a), Qy) + (syxEdge ? bit_get(A1, a, b) : 0);

        int dx = 0;
        for (int w : g2[x]) {
            if (w == y) continue;
            dx += bit_get(A1, p[w], b) - bit_get(A1, p[w], a);
        }
        int dy = 0;
        for (int w : g2[y]) {
            if (w == x) continue;
            dy += bit_get(A1, p[w], a) - bit_get(A1, p[w], b);
        }
        int delta_dbl = (Sx_new + Sy_new - Sx_old - Sy_old) + dx + dy;
        if (delta_dbl > 0) {
            // commit swap
            // Update S for x and y
            S[x] = Sx_new;
            S[y] = Sy_new;

            // Update S for neighbors and update Q for affected vertices
            static vector<unsigned char> mark;
            static vector<int> touched;
            if ((int)mark.size() < n) mark.assign(n, 0);
            touched.clear();
            auto touch = [&](int w, unsigned char bit){
                if (!(mark[w] & bit)) {
                    mark[w] |= bit;
                    if (mark[w] == bit) touched.push_back(w);
                } else {
                    mark[w] |= bit;
                }
            };

            for (int w : g2[x]) {
                if (w != y) {
                    S[w] += bit_get(A1, p[w], b) - bit_get(A1, p[w], a);
                }
                touch(w, 1);
            }
            for (int w : g2[y]) {
                if (w != x) {
                    S[w] += bit_get(A1, p[w], a) - bit_get(A1, p[w], b);
                }
                touch(w, 2);
            }

            // Update Q[w]: bit 'a' becomes neighbor-of-y, bit 'b' becomes neighbor-of-x
            for (int w : touched) {
                bool nx = (mark[w] & 1);
                bool ny = (mark[w] & 2);
                bit_assign(Q, w, a, ny);
                bit_assign(Q, w, b, nx);
                mark[w] = 0;
            }

            // Update permutation
            p[x] = b; p[y] = a;
            invp[a] = y; invp[b] = x;

            matched_dbl += delta_dbl;
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}