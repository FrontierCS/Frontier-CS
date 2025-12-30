#include <bits/stdc++.h>
using namespace std;

static constexpr int R = 8, C = 14, N = R * C;

struct Mask {
    uint64_t lo = 0, hi = 0;
};
static inline Mask operator|(const Mask& a, const Mask& b) { return {a.lo | b.lo, a.hi | b.hi}; }
static inline Mask operator&(const Mask& a, const Mask& b) { return {a.lo & b.lo, a.hi & b.hi}; }
static inline Mask& operator|=(Mask& a, const Mask& b) { a.lo |= b.lo; a.hi |= b.hi; return a; }
static inline bool emptyMask(const Mask& m) { return (m.lo | m.hi) == 0; }

static inline void setBit(Mask& m, int idx) {
    if (idx < 64) m.lo |= (1ULL << idx);
    else m.hi |= (1ULL << (idx - 64));
}

array<Mask, N> adjMask;

static inline Mask unionAdj(const Mask& cur) {
    Mask reach{0, 0};
    uint64_t x = cur.lo;
    while (x) {
        int b = __builtin_ctzll(x);
        x &= x - 1;
        reach |= adjMask[b];
    }
    x = cur.hi;
    while (x) {
        int b = __builtin_ctzll(x);
        x &= x - 1;
        reach |= adjMask[64 + b];
    }
    return reach;
}

static inline array<Mask, 10> buildDigitMasks(const array<uint8_t, N>& digits) {
    array<Mask, 10> dm{};
    for (int i = 0; i < N; i++) setBit(dm[digits[i]], i);
    return dm;
}

static inline bool readable(const string& s, const array<Mask, 10>& dm) {
    int d0 = s[0] - '0';
    Mask cur = dm[d0];
    if (emptyMask(cur)) return false;
    for (size_t i = 1; i < s.size(); i++) {
        int nd = s[i] - '0';
        Mask reach = unionAdj(cur);
        cur = reach & dm[nd];
        if (emptyMask(cur)) return false;
    }
    return true;
}

static inline int computeScore(const array<uint8_t, N>& digits,
                               const vector<string>& nums,
                               int cap,
                               int threshold) {
    auto dm = buildDigitMasks(digits);
    int upto = min(cap, threshold);
    for (int k = 1; k <= upto; k++) {
        if (!readable(nums[k], dm)) return k - 1;
    }
    for (int k = upto + 1; k <= cap; k++) {
        if (!readable(nums[k], dm)) return k - 1;
    }
    return cap;
}

static inline array<uint8_t, N> randomGrid(mt19937_64& rng) {
    array<uint8_t, N> g{};
    for (int i = 0; i < N; i++) g[i] = (uint8_t)(rng() % 10);

    array<int, 10> cnt{};
    for (int i = 0; i < N; i++) cnt[g[i]]++;
    for (int d = 0; d <= 9; d++) {
        if (cnt[d] == 0) {
            int idx = (int)(rng() % N);
            cnt[g[idx]]--;
            g[idx] = (uint8_t)d;
            cnt[d]++;
        }
    }
    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute adjacency masks (8 directions)
    for (int r = 0; r < R; r++) {
        for (int c = 0; c < C; c++) {
            int idx = r * C + c;
            Mask m{0, 0};
            for (int dr = -1; dr <= 1; dr++) for (int dc = -1; dc <= 1; dc++) {
                if (dr == 0 && dc == 0) continue;
                int nr = r + dr, nc = c + dc;
                if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                    int j = nr * C + nc;
                    setBit(m, j);
                }
            }
            adjMask[idx] = m;
        }
    }

    constexpr int CAP = 5000;
    vector<string> nums(CAP + 1);
    for (int i = 1; i <= CAP; i++) nums[i] = to_string(i);

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 7) ^ (seed >> 9) ^ 0x9e3779b97f4a7c15ULL;
    mt19937_64 rng(seed);

    auto start = chrono::high_resolution_clock::now();
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::high_resolution_clock::now() - start).count();
    };

    const double TIME_LIMIT = 0.75;

    array<uint8_t, N> best{};
    {
        // Base pattern with mild structure + randomness
        for (int r = 0; r < R; r++) for (int c = 0; c < C; c++) {
            int idx = r * C + c;
            uint64_t v = rng();
            best[idx] = (uint8_t)((int)((r * 7 + c * 3 + (int)(v % 10)) % 10));
        }
        // Ensure all digits exist
        array<int, 10> cnt{};
        for (int i = 0; i < N; i++) cnt[best[i]]++;
        for (int d = 0; d <= 9; d++) if (cnt[d] == 0) best[(int)(rng() % N)] = (uint8_t)d;
    }

    int bestScore = computeScore(best, nums, CAP, 0);
    array<uint8_t, N> cur = best;
    int curScore = bestScore;

    // Random restarts
    while (elapsedSec() < TIME_LIMIT * 0.35) {
        auto g = randomGrid(rng);
        int sc = computeScore(g, nums, CAP, bestScore);
        if (sc > bestScore) {
            bestScore = sc;
            best = g;
            cur = best;
            curScore = bestScore;
        }
    }

    // Hillclimb / annealing
    double T0 = 5.0;
    double Tend = 0.2;
    int iter = 0;
    while (elapsedSec() < TIME_LIMIT) {
        iter++;
        double t = elapsedSec() / TIME_LIMIT;
        double T = T0 * pow(Tend / T0, t);

        int pos = (int)(rng() % N);
        uint8_t old = cur[pos];
        uint8_t nd = (uint8_t)(rng() % 10);
        if (nd == old) continue;

        cur[pos] = nd;

        int newScore = computeScore(cur, nums, CAP, curScore);
        int delta = newScore - curScore;

        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp((double)delta / max(1e-9, T));
            uint64_t rv = rng();
            double u = (rv >> 11) * (1.0 / 9007199254740992.0); // [0,1)
            accept = (u < prob);
        }

        if (accept) {
            curScore = newScore;
            if (curScore > bestScore) {
                bestScore = curScore;
                best = cur;
            }
        } else {
            cur[pos] = old;
        }
    }

    for (int r = 0; r < R; r++) {
        for (int c = 0; c < C; c++) {
            cout << char('0' + best[r * C + c]);
        }
        cout << '\n';
    }
    return 0;
}