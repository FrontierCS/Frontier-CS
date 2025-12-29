#include <bits/stdc++.h>
using namespace std;

static const int R = 8;
static const int C = 14;
static const int N = R * C;

struct Bits {
    uint64_t lo = 0, hi = 0;
    inline bool none() const { return (lo | hi) == 0; }
    inline void reset() { lo = 0; hi = 0; }
};

inline void setbit(Bits &b, int pos) {
    if (pos < 64) b.lo |= (1ULL << pos);
    else b.hi |= (1ULL << (pos - 64));
}

struct GridSolver {
    // adjacency bitsets per cell
    vector<Bits> adj;
    // masks per digit
    array<Bits, 10> masks{};
    // grid digits
    array<uint8_t, N> g{};
    // best grid
    array<uint8_t, N> best_g{};
    int best_score = -1;

    // precomputed digits for numbers 1..MAX_PRE
    static const int MAX_PRE = 5000;
    vector<vector<uint8_t>> preDigits;

    mt19937_64 rng;

    GridSolver() {
        uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
        rng.seed(seed);
        buildAdj();
        precomputeDigits();
    }

    void buildAdj() {
        adj.assign(N, Bits{});
        auto inb = [&](int r, int c){ return r >= 0 && r < R && c >= 0 && c < C; };
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                int u = r * C + c;
                for (int dr = -1; dr <= 1; ++dr) {
                    for (int dc = -1; dc <= 1; ++dc) {
                        if (dr == 0 && dc == 0) continue;
                        int nr = r + dr, nc = c + dc;
                        if (inb(nr, nc)) {
                            int v = nr * C + nc;
                            setbit(adj[u], v);
                        }
                    }
                }
            }
        }
    }

    void precomputeDigits() {
        preDigits.resize(MAX_PRE + 1);
        for (int n = 1; n <= MAX_PRE; ++n) {
            int x = n;
            vector<uint8_t> ds;
            while (x > 0) { ds.push_back((uint8_t)(x % 10)); x /= 10; }
            reverse(ds.begin(), ds.end());
            preDigits[n] = move(ds);
        }
    }

    inline const vector<uint8_t>& getDigits(int n, vector<uint8_t>& tmp) {
        if (n <= MAX_PRE) return preDigits[n];
        tmp.clear();
        int x = n;
        while (x > 0) { tmp.push_back((uint8_t)(x % 10)); x /= 10; }
        reverse(tmp.begin(), tmp.end());
        return tmp;
    }

    void computeMasks() {
        for (int d = 0; d < 10; ++d) { masks[d].reset(); }
        for (int i = 0; i < N; ++i) {
            setbit(masks[g[i]], i);
        }
    }

    inline void updateMaskAt(int idx, uint8_t oldd, uint8_t newd) {
        if (idx < 64) {
            masks[oldd].lo &= ~(1ULL << idx);
            masks[newd].lo |=  (1ULL << idx);
        } else {
            int j = idx - 64;
            masks[oldd].hi &= ~(1ULL << j);
            masks[newd].hi |=  (1ULL << j);
        }
    }

    bool readableDigits(const vector<uint8_t>& ds) {
        Bits S = masks[ds[0]];
        if (S.none()) return false;
        for (size_t k = 1; k < ds.size(); ++k) {
            Bits T; T.reset();
            uint64_t w = S.lo;
            while (w) {
                int i = __builtin_ctzll(w);
                T.lo |= adj[i].lo;
                T.hi |= adj[i].hi;
                w &= w - 1;
            }
            w = S.hi;
            while (w) {
                int i = __builtin_ctzll(w);
                int idx = 64 + i;
                T.lo |= adj[idx].lo;
                T.hi |= adj[idx].hi;
                w &= w - 1;
            }
            S.lo = T.lo & masks[ds[k]].lo;
            S.hi = T.hi & masks[ds[k]].hi;
            if (S.none()) return false;
        }
        return true;
    }

    int evaluate(int mustAtLeast, int extraMargin, int maxN) {
        // quick check: ensure digits 1..9 exist for 1-digit numbers
        for (int d = 1; d <= 9; ++d) {
            if (masks[d].none()) return 0;
        }
        int n = 1;
        vector<uint8_t> tmp;
        for (; n <= mustAtLeast; ++n) {
            const auto& ds = getDigits(n, tmp);
            if (!readableDigits(ds)) return n - 1;
        }
        int limit = min(maxN, mustAtLeast + extraMargin);
        for (; n <= limit; ++n) {
            const auto& ds = getDigits(n, tmp);
            if (!readableDigits(ds)) return n - 1;
        }
        // if reached limit, keep going a bit more until failure or maxN
        for (; n <= maxN; ++n) {
            const auto& ds = getDigits(n, tmp);
            if (!readableDigits(ds)) return n - 1;
        }
        return maxN;
    }

    void initGrid() {
        // Start with a snake pattern repeating 0..9
        for (int r = 0; r < R; ++r) {
            if (r % 2 == 0) {
                for (int c = 0; c < C; ++c) {
                    int i = r * C + c;
                    g[i] = (uint8_t)((i) % 10);
                }
            } else {
                for (int c = 0; c < C; ++c) {
                    int i = r * C + (C - 1 - c);
                    g[r * C + c] = (uint8_t)((i) % 10);
                }
            }
        }
        // Ensure at least one of each digit 0..9 exists
        array<int, 10> cnt{};
        for (int i = 0; i < N; ++i) cnt[g[i]]++;
        for (int d = 0; d < 10; ++d) {
            if (cnt[d] == 0) {
                int pos = rng() % N;
                cnt[g[pos]]--;
                g[pos] = (uint8_t)d;
                cnt[d]++;
            }
        }
        // Add some randomization
        for (int k = 0; k < N; ++k) {
            if ((rng() & 1) == 0) continue;
            int i = rng() % N;
            g[i] = (uint8_t)(rng() % 10);
        }
        computeMasks();
        best_g = g;
        best_score = evaluate(0, 300, 10000);
    }

    void optimize(double timeLimitSec) {
        auto start = chrono::steady_clock::now();
        double elapsed = 0.0;

        uniform_int_distribution<int> posDist(0, N - 1);
        uniform_int_distribution<int> digDist(0, 9);

        int mustAtLeast = max(0, best_score - 10);
        const int extraMarginBase = 200;
        const int maxN = 10000;

        while (true) {
            auto now = chrono::steady_clock::now();
            elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > timeLimitSec) break;

            int idx = posDist(rng);
            uint8_t oldd = g[idx];
            uint8_t newd = (uint8_t)digDist(rng);
            if (newd == oldd) continue;

            g[idx] = newd;
            // incremental mask update
            updateMaskAt(idx, oldd, newd);

            int extraMargin = extraMarginBase;
            // try evaluate early with mustAtLeast slightly below best to allow improvements
            int sc = evaluate(mustAtLeast, extraMargin, maxN);
            if (sc > best_score) {
                best_score = sc;
                best_g = g;
                mustAtLeast = max(0, best_score - 10);
            } else {
                // revert
                g[idx] = oldd;
                updateMaskAt(idx, newd, oldd);
            }
        }
        // finalize to best
        g = best_g;
        computeMasks();
    }

    void printGrid() {
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                cout << char('0' + g[r * C + c]);
            }
            cout << '\n';
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    GridSolver solver;
    solver.initGrid();
    // Use a modest time budget to avoid risking TLE; adjust if needed
    solver.optimize(0.6);
    solver.printGrid();
    return 0;
}