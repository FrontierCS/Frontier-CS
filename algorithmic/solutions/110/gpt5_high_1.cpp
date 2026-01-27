#include <bits/stdc++.h>
using namespace std;

static const int H = 8, W = 14, N = H * W;

struct Bits {
    uint64_t lo, hi;
    inline void clear() { lo = 0; hi = 0; }
    inline bool any() const { return (lo | hi) != 0ULL; }
    inline void set(int idx) {
        if (idx < 64) lo |= (1ULL << idx);
        else hi |= (1ULL << (idx - 64));
    }
    inline void ORwith(const Bits &b) { lo |= b.lo; hi |= b.hi; }
    inline void ANDwith(const Bits &b) { lo &= b.lo; hi &= b.hi; }
};

struct Grid {
    array<unsigned char, N> a;
};

static Bits neighMask[N];

inline int idxOf(int r, int c) { return r * W + c; }

void initNeighbors() {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int i = idxOf(r, c);
            Bits b; b.clear();
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr, nc = c + dc;
                    if (nr >= 0 && nr < H && nc >= 0 && nc < W) {
                        b.set(idxOf(nr, nc));
                    }
                }
            }
            neighMask[i] = b;
        }
    }
}

struct EvalContext {
    Bits digitMask[10];
};

void buildDigitMasks(const Grid &g, EvalContext &ctx) {
    for (int d = 0; d < 10; ++d) ctx.digitMask[d].clear();
    for (int i = 0; i < N; ++i) {
        ctx.digitMask[g.a[i]].set(i);
    }
}

inline void digitsOf(int n, unsigned char out[], int &len) {
    unsigned char tmp[16];
    int l = 0;
    while (n > 0) {
        tmp[l++] = (unsigned char)(n % 10);
        n /= 10;
    }
    len = l;
    for (int i = 0; i < l; ++i) out[i] = tmp[l - 1 - i];
}

inline void unionNeighbors(const Bits &S, Bits &U) {
    U.clear();
    uint64_t x = S.lo;
    while (x) {
        int b = __builtin_ctzll(x);
        U.ORwith(neighMask[b]);
        x &= x - 1;
    }
    x = S.hi;
    while (x) {
        int b = __builtin_ctzll(x) + 64;
        U.ORwith(neighMask[b]);
        x &= x - 1;
    }
}

inline bool readable(const EvalContext &ctx, const unsigned char digs[], int len) {
    Bits S = ctx.digitMask[digs[0]];
    if (!S.any()) return false;
    for (int i = 1; i < len; ++i) {
        Bits U;
        unionNeighbors(S, U);
        U.ANDwith(ctx.digitMask[digs[i]]);
        if (!U.any()) return false;
        S = U;
    }
    return true;
}

int scoreGrid(const Grid &g, int limitN) {
    EvalContext ctx;
    buildDigitMasks(g, ctx);
    unsigned char digs[16];
    int len = 0;
    for (int n = 1; n <= limitN; ++n) {
        digitsOf(n, digs, len);
        if (!readable(ctx, digs, len)) {
            return n - 1;
        }
    }
    return limitN;
}

int scoreGridFull(const Grid &g, int hardCap, double timeBudgetSec, chrono::steady_clock::time_point endTime) {
    EvalContext ctx;
    buildDigitMasks(g, ctx);
    unsigned char digs[16];
    int len = 0;
    int n = 1;
    // Adaptive stepping to save time
    int step = 1000;
    int lastConfirmed = 0;
    while (true) {
        int target = min(hardCap, n + step - 1);
        for (; n <= target; ++n) {
            if ((n & 1023) == 0) {
                if (chrono::steady_clock::now() > endTime) return n - 1;
            }
            digitsOf(n, digs, len);
            if (!readable(ctx, digs, len)) return n - 1;
        }
        lastConfirmed = n - 1;
        if (step < 100000) step *= 2;
        if (lastConfirmed >= hardCap) return hardCap;
        if (chrono::steady_clock::now() > endTime) return lastConfirmed;
    }
}

void randomGrid(Grid &g, mt19937_64 &rng) {
    uniform_int_distribution<int> dist(0, 9);
    for (int i = 0; i < N; ++i) g.a[i] = (unsigned char)dist(rng);
}

void patternedGrid(Grid &g) {
    // Simple deterministic pattern to ensure diversity in neighbors
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = (r * W + c) % 10;
            g.a[idxOf(r, c)] = (unsigned char)v;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    initNeighbors();

    auto t0 = chrono::steady_clock::now();
    // Reserve about 57 seconds for computation
    double totalBudgetSec = 57.0;
    auto endTime = t0 + chrono::milliseconds((int)(totalBudgetSec * 1000));

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 13) ^ (seed >> 7) ^ (seed << 17);
    mt19937_64 rng(seed);

    Grid bestGrid;
    int bestScore = -1;

    // Try an initial patterned grid
    {
        Grid g;
        patternedGrid(g);
        int s = scoreGrid(g, 5000);
        if (s > bestScore) { bestScore = s; bestGrid = g; }
    }

    int quickLimit = 6000; // quick evaluation limit per random grid
    // Random search phase
    while (chrono::steady_clock::now() < endTime) {
        Grid g;
        randomGrid(g, rng);
        int s = scoreGrid(g, quickLimit);
        if (s > bestScore) {
            bestScore = s;
            bestGrid = g;
        }
        // Occasionally refine promising grids
        if (s >= quickLimit) {
            // Do a deeper check on this grid
            auto now = chrono::steady_clock::now();
            double remaining = chrono::duration<double>(endTime - now).count();
            if (remaining <= 0.0) break;
            int deepCap = 200000; // upper cap for deeper scoring
            int fullScore = scoreGridFull(g, deepCap, remaining, endTime);
            if (fullScore > bestScore) {
                bestScore = fullScore;
                bestGrid = g;
            }
        }
        // Periodically try a small local mutation from the current best
        if ((rng() & 1023ULL) == 0ULL) {
            Grid mutated = bestGrid;
            uniform_int_distribution<int> idxDist(0, N - 1);
            uniform_int_distribution<int> digDist(0, 9);
            int changes = 5;
            for (int k = 0; k < changes; ++k) {
                int idx = idxDist(rng);
                mutated.a[idx] = (unsigned char)digDist(rng);
            }
            int s2 = scoreGrid(mutated, quickLimit);
            if (s2 >= bestScore) {
                // deeper check
                auto now = chrono::steady_clock::now();
                double remaining = chrono::duration<double>(endTime - now).count();
                if (remaining <= 0.0) break;
                int deepCap = 200000;
                int fullScore = scoreGridFull(mutated, deepCap, remaining, endTime);
                if (fullScore > bestScore) {
                    bestScore = fullScore;
                    bestGrid = mutated;
                }
            }
        }
    }

    // Print the best grid found
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            cout << char('0' + bestGrid.a[idxOf(r, c)]);
        }
        cout << '\n';
    }

    return 0;
}