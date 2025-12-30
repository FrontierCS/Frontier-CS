#include <bits/stdc++.h>
using namespace std;

static const int R = 8;
static const int C = 14;
static const int N = R * C;

struct BS {
    uint64_t lo, hi;
    BS() : lo(0), hi(0) {}
    inline void reset() { lo = 0; hi = 0; }
    inline bool any() const { return (lo | hi) != 0ULL; }
    inline void set(int idx) {
        if (idx < 64) lo |= (1ULL << idx);
        else hi |= (1ULL << (idx - 64));
    }
    inline void orEq(const BS &o) {
        lo |= o.lo;
        hi |= o.hi;
    }
};

struct Grid {
    array<int, N> digit;
    vector<array<BS, 10>> rowAdj; // rowAdj[i][d] = neighbors of i that have digit d
    array<BS, 10> startSet;       // startSet[d] = cells with digit d
    vector<vector<int>> neigh;    // adjacency list

    Grid() {
        neigh.assign(N, {});
        buildNeighbors();
        rowAdj.assign(N, {});
    }

    inline int idx(int r, int c) { return r * C + c; }

    void buildNeighbors() {
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                int i = idx(r, c);
                for (int dr = -1; dr <= 1; ++dr) {
                    for (int dc = -1; dc <= 1; ++dc) {
                        if (dr == 0 && dc == 0) continue;
                        int nr = r + dr, nc = c + dc;
                        if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                            int j = idx(nr, nc);
                            neigh[i].push_back(j);
                        }
                    }
                }
            }
        }
    }

    void randomInit(mt19937 &rng) {
        uniform_int_distribution<int> dist(0, 9);
        for (int i = 0; i < N; ++i) digit[i] = dist(rng);
        // Ensure digits 1..9 appear at least once
        array<int, 10> cnt{}; cnt.fill(0);
        for (int i = 0; i < N; ++i) cnt[digit[i]]++;
        for (int d = 1; d <= 9; ++d) {
            if (cnt[d] == 0) {
                // replace a random cell (prefer a digit with count > 1)
                int pos = -1;
                for (int tries = 0; tries < 1000; ++tries) {
                    int t = rng() % N;
                    if (cnt[digit[t]] > 1) { pos = t; break; }
                }
                if (pos == -1) pos = rng() % N;
                cnt[digit[pos]]--;
                digit[pos] = d;
                cnt[d]++;
            }
        }
    }

    void rebuildAdj() {
        for (int d = 0; d < 10; ++d) { startSet[d].reset(); }
        for (int i = 0; i < N; ++i) {
            startSet[digit[i]].set(i);
        }
        for (int i = 0; i < N; ++i) {
            for (int d = 0; d < 10; ++d) {
                rowAdj[i][d].reset();
            }
            for (int j : neigh[i]) {
                int d = digit[j];
                rowAdj[i][d].set(j);
            }
        }
    }

    inline BS step(const BS &S, int d) const {
        BS out;
        uint64_t x = S.lo;
        while (x) {
            int i = __builtin_ctzll(x);
            x &= (x - 1);
            out.orEq(rowAdj[i][d]);
        }
        x = S.hi;
        while (x) {
            int i = __builtin_ctzll(x) + 64;
            x &= (x - 1);
            out.orEq(rowAdj[i][d]);
        }
        return out;
    }

    int evaluateX(const vector<uint8_t> &digitsBuf, const vector<uint32_t> &offs, int maxCheck) const {
        for (int k = 1; k <= maxCheck; ++k) {
            uint32_t st = offs[k - 1], ed = offs[k];
            if (st >= ed) continue;
            int first = digitsBuf[st];
            BS S = startSet[first];
            if (!S.any()) return k - 1;
            for (uint32_t p = st + 1; p < ed; ++p) {
                S = step(S, digitsBuf[p]);
                if (!S.any()) return k - 1;
            }
        }
        return maxCheck;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Time budget (soft), we won't actually use the full 60s; keep it short but dynamic.
    auto t_start = chrono::steady_clock::now();
    const auto soft_budget = chrono::milliseconds(800); // keep runtime small

    // Precompute digits for numbers 1..MaxCheck
    const int MaxCheck = 100000; // sufficient to distinguish good grids; keeps evaluation fast
    vector<uint32_t> offs(MaxCheck + 1, 0);
    vector<uint8_t> digitsBuf;
    digitsBuf.reserve(500000); // rough estimate
    for (int k = 1; k <= MaxCheck; ++k) {
        int x = k;
        uint8_t tmp[16];
        int len = 0;
        while (x > 0) { tmp[len++] = (uint8_t)(x % 10); x /= 10; }
        for (int i = len - 1; i >= 0; --i) digitsBuf.push_back(tmp[i]);
        offs[k] = (uint32_t)digitsBuf.size();
    }

    // RNG
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    seed ^= (uint64_t)random_device{}();
    mt19937 rng((uint32_t)seed);

    Grid g;
    Grid best = g;
    int bestX = -1;

    int attempts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        if (now - t_start > soft_budget) break;
        ++attempts;

        g.randomInit(rng);
        g.rebuildAdj();
        int X = g.evaluateX(digitsBuf, offs, MaxCheck);
        if (X > bestX) {
            bestX = X;
            best = g;
            // If we already reach MaxCheck, it's good enough; we can stop early.
            if (bestX >= MaxCheck) break;
        }
    }

    // Output the best grid found
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << best.digit[r * C + c];
        }
        cout << '\n';
    }
    return 0;
}