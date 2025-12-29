#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed ? seed : 88172645463325252ull) {}
    inline uint64_t nextU64() {
        uint64_t y = x;
        y ^= y << 7;
        y ^= y >> 9;
        return x = y;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Bits {
    uint64_t lo = 0, hi = 0; // bits [0..63], [64..127)
    inline bool empty() const { return (lo | hi) == 0; }
    inline void set(int idx) {
        if (idx < 64) lo |= (1ULL << idx);
        else hi |= (1ULL << (idx - 64));
    }
    inline Bits& operator|=(const Bits& o) { lo |= o.lo; hi |= o.hi; return *this; }
};

static inline Bits operator&(const Bits& a, const Bits& b) { return Bits{a.lo & b.lo, a.hi & b.hi}; }

static constexpr int R = 8, C = 14, N = R * C;

array<Bits, N> adjBits;
array<array<int, 8>, N> neighArr;
array<int, N> neighDeg;

static inline Bits unionNeighbors(const Bits& cur) {
    Bits res;
    uint64_t x = cur.lo;
    while (x) {
        int b = __builtin_ctzll(x);
        res |= adjBits[b];
        x &= (x - 1);
    }
    x = cur.hi;
    while (x) {
        int b = __builtin_ctzll(x);
        res |= adjBits[64 + b];
        x &= (x - 1);
    }
    return res;
}

static vector<vector<uint8_t>> numDigits; // 1..cap

static inline int computeScore(const vector<int>& grid, int cap, vector<uint8_t>* failDigits = nullptr) {
    array<Bits, 10> masks;
    for (int i = 0; i < N; i++) masks[grid[i]].set(i);

    for (int x = 1; x <= cap; x++) {
        const auto& digs = numDigits[x];
        Bits cur = masks[digs[0]];
        if (cur.empty()) {
            if (failDigits) *failDigits = digs;
            return x - 1;
        }
        for (int k = 1; k < (int)digs.size(); k++) {
            Bits nb = unionNeighbors(cur);
            cur = nb & masks[digs[k]];
            if (cur.empty()) break;
        }
        if (cur.empty()) {
            if (failDigits) *failDigits = digs;
            return x - 1;
        }
    }
    if (failDigits) failDigits->clear();
    return cap;
}

static inline vector<int> seedGrid(XorShift64& rng) {
    vector<int> g(N);
    for (int i = 0; i < N; i++) g[i] = rng.nextInt(10);

    // Add small clusters for each digit to ensure repeatability and adjacency.
    for (int d = 0; d <= 9; d++) {
        int s = rng.nextInt(N);
        g[s] = d;
        int cur = s;
        for (int t = 0; t < 3; t++) {
            int deg = neighDeg[cur];
            if (deg == 0) break;
            int nxt = neighArr[cur][rng.nextInt(deg)];
            g[nxt] = d;
            cur = nxt;
        }
    }

    // Ensure digits 1..9 exist at least twice, and 0 exists at least once.
    array<int, 10> cnt{};
    for (int v : g) cnt[v]++;
    auto forceDigit = [&](int d) {
        int pos = rng.nextInt(N);
        cnt[g[pos]]--;
        g[pos] = d;
        cnt[d]++;
    };
    if (cnt[0] == 0) forceDigit(0);
    for (int d = 1; d <= 9; d++) while (cnt[d] < 2) forceDigit(d);
    return g;
}

static inline void mutateSmall(vector<int>& cand, XorShift64& rng) {
    int changes = 1 + rng.nextInt(3);
    for (int t = 0; t < changes; t++) {
        int idx = rng.nextInt(N);
        int nd = rng.nextInt(10);
        cand[idx] = nd;
    }
}

static inline void mutateSwap(vector<int>& cand, XorShift64& rng) {
    int a = rng.nextInt(N), b = rng.nextInt(N);
    if (a != b) swap(cand[a], cand[b]);
}

static inline void mutateGuidedPath(vector<int>& cand, const vector<int>& base, const vector<uint8_t>& target, XorShift64& rng) {
    if (target.empty()) return;
    int L = (int)target.size();
    if (L <= 0) return;

    vector<int> bestPath(L);
    int bestZeros = -1;

    // Build a path preferring cells with digit 0 in the base grid.
    for (int attempt = 0; attempt < 30; attempt++) {
        vector<int> path(L);
        int start = rng.nextInt(N);
        // try to start from a zero cell occasionally
        if (rng.nextInt(100) < 75) {
            for (int t = 0; t < 5; t++) {
                int p = rng.nextInt(N);
                if (base[p] == 0) { start = p; break; }
            }
        }
        path[0] = start;
        int zeros = (base[start] == 0);
        for (int i = 1; i < L; i++) {
            int cur = path[i - 1];
            int deg = neighDeg[cur];
            if (deg == 0) { path[i] = cur; continue; }
            int nxt;
            if (rng.nextInt(100) < 75) {
                // prefer neighbor that is 0
                nxt = neighArr[cur][rng.nextInt(deg)];
                for (int tries = 0; tries < 6; tries++) {
                    int v = neighArr[cur][rng.nextInt(deg)];
                    if (base[v] == 0) { nxt = v; break; }
                }
            } else {
                nxt = neighArr[cur][rng.nextInt(deg)];
            }
            path[i] = nxt;
            zeros += (base[nxt] == 0);
        }
        if (zeros > bestZeros) {
            bestZeros = zeros;
            bestPath = path;
        }
    }

    for (int i = 0; i < L; i++) cand[bestPath[i]] = (int)target[i];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Build adjacency (8 directions)
    for (int r = 0; r < R; r++) {
        for (int c = 0; c < C; c++) {
            int id = r * C + c;
            neighDeg[id] = 0;
            for (int dr = -1; dr <= 1; dr++) {
                for (int dc = -1; dc <= 1; dc++) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr, nc = c + dc;
                    if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                        int nid = nr * C + nc;
                        adjBits[id].set(nid);
                        if (neighDeg[id] < 8) neighArr[id][neighDeg[id]++] = nid;
                    }
                }
            }
        }
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    seed ^= (uint64_t)clock();
    XorShift64 rng(seed);

    int cap = 5000;
    numDigits.assign(cap + 1, {});
    for (int i = 1; i <= cap; i++) {
        int x = i;
        vector<uint8_t> digs;
        while (x > 0) {
            digs.push_back((uint8_t)(x % 10));
            x /= 10;
        }
        reverse(digs.begin(), digs.end());
        numDigits[i] = move(digs);
    }

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 57.0;

    vector<int> bestGrid = seedGrid(rng);
    vector<uint8_t> bestFail;
    int bestScore = computeScore(bestGrid, cap, &bestFail);

    vector<int> curGrid = bestGrid;
    vector<uint8_t> curFail = bestFail;
    int curScore = bestScore;

    int noImprove = 0;
    int iters = 0;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= TIME_LIMIT_SEC) break;

        double t = elapsed / TIME_LIMIT_SEC;
        double T0 = 12.0, T1 = 0.2;
        double T = T0 * pow(T1 / T0, t);

        vector<int> cand = curGrid;

        int mt = rng.nextInt(100);
        if (mt < 55) {
            mutateSmall(cand, rng);
        } else if (mt < 75) {
            mutateSwap(cand, rng);
        } else {
            // guided mutation toward current failing number (recompute occasionally)
            if (curFail.empty() || (iters % 40 == 0)) computeScore(curGrid, cap, &curFail);
            mutateGuidedPath(cand, curGrid, curFail, rng);
            if (rng.nextInt(100) < 50) mutateSmall(cand, rng);
        }

        int candScore = computeScore(cand, cap, nullptr);
        int delta = candScore - curScore;

        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp((double)delta / max(1e-9, T));
            if (rng.nextDouble() < prob) accept = true;
        }

        if (accept) {
            curGrid.swap(cand);
            curScore = candScore;
            if (delta != 0) curFail.clear();
        }

        if (candScore > bestScore) {
            bestScore = candScore;
            bestGrid = accept ? curGrid : cand;
            computeScore(bestGrid, cap, &bestFail);
            noImprove = 0;
        } else {
            noImprove++;
        }

        // Random restart if stuck
        if (noImprove > 2500 && elapsed + 0.5 < TIME_LIMIT_SEC) {
            curGrid = seedGrid(rng);
            curScore = computeScore(curGrid, cap, &curFail);
            noImprove = 0;
        }

        iters++;
    }

    for (int r = 0; r < R; r++) {
        for (int c = 0; c < C; c++) {
            cout << char('0' + bestGrid[r * C + c]);
        }
        cout << '\n';
    }
    return 0;
}