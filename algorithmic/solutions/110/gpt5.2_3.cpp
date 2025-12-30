#include <bits/stdc++.h>
using namespace std;

static constexpr int H = 8, W = 14, N = H * W;
static constexpr int MAXCHECK = 20000;

struct Bits {
    uint64_t w0 = 0, w1 = 0;
};
static inline Bits band(const Bits& a, const Bits& b) { return Bits{a.w0 & b.w0, a.w1 & b.w1}; }
static inline Bits bor(const Bits& a, const Bits& b) { return Bits{a.w0 | b.w0, a.w1 | b.w1}; }
static inline void ior(Bits& a, const Bits& b) { a.w0 |= b.w0; a.w1 |= b.w1; }
static inline bool none(const Bits& a) { return (a.w0 | a.w1) == 0; }
static inline void setBit(Bits& a, int i) { (i < 64 ? a.w0 : a.w1) |= (1ULL << (i & 63)); }
static inline void clrBit(Bits& a, int i) { (i < 64 ? a.w0 : a.w1) &= ~(1ULL << (i & 63)); }

static array<Bits, N> neighMask;

struct State {
    array<uint8_t, N> cell{};
    array<Bits, 10> digitMask{};
};

static vector<vector<uint8_t>> numDigits;

static inline bool canRead(const State& st, const vector<uint8_t>& seq) {
    Bits cur = st.digitMask[seq[0]];
    if (none(cur)) return false;

    for (size_t i = 1; i < seq.size(); ++i) {
        const Bits& target = st.digitMask[seq[i]];
        Bits nxt{};
        uint64_t x = cur.w0;
        while (x) {
            int b = __builtin_ctzll(x);
            int idx = b;
            ior(nxt, band(neighMask[idx], target));
            x &= x - 1;
        }
        x = cur.w1;
        while (x) {
            int b = __builtin_ctzll(x);
            int idx = 64 + b;
            if (idx < N) ior(nxt, band(neighMask[idx], target));
            x &= x - 1;
        }
        cur = nxt;
        if (none(cur)) return false;
    }
    return true;
}

static inline int evalUpTo(const State& st, int limit) {
    limit = min(limit, MAXCHECK);
    for (int n = 1; n <= limit; ++n) {
        if (!canRead(st, numDigits[n])) return n - 1;
    }
    return limit;
}
static inline int evalContinue(const State& st, int from) {
    from = min(from, MAXCHECK);
    for (int n = from + 1; n <= MAXCHECK; ++n) {
        if (!canRead(st, numDigits[n])) return n - 1;
    }
    return MAXCHECK;
}
static inline int evalFull(const State& st) {
    return evalContinue(st, 0);
}

static inline void rebuildMasks(State& st) {
    for (int d = 0; d < 10; ++d) st.digitMask[d] = Bits{};
    for (int i = 0; i < N; ++i) setBit(st.digitMask[st.cell[i]], i);
}

static inline void setDigit(State& st, int pos, uint8_t nd) {
    uint8_t od = st.cell[pos];
    if (od == nd) return;
    clrBit(st.digitMask[od], pos);
    setBit(st.digitMask[nd], pos);
    st.cell[pos] = nd;
}

static inline void swapDigits(State& st, int i, int j) {
    if (i == j) return;
    uint8_t a = st.cell[i], b = st.cell[j];
    if (a == b) return;
    clrBit(st.digitMask[a], i);
    clrBit(st.digitMask[b], j);
    setBit(st.digitMask[a], j);
    setBit(st.digitMask[b], i);
    st.cell[i] = b;
    st.cell[j] = a;
}

static bool hasAdjPairDigit(const State& st, int d) {
    for (int i = 0; i < N; ++i) {
        if (st.cell[i] != d) continue;
        Bits nb = neighMask[i];
        uint64_t x = nb.w0;
        while (x) {
            int b = __builtin_ctzll(x);
            int j = b;
            if (st.cell[j] == d) return true;
            x &= x - 1;
        }
        x = nb.w1;
        while (x) {
            int b = __builtin_ctzll(x);
            int j = 64 + b;
            if (j < N && st.cell[j] == d) return true;
            x &= x - 1;
        }
    }
    return false;
}

static State makePatternState(int mode) {
    State st;
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = 0;
            if (mode == 0) v = (r + c) % 10;
            else if (mode == 1) v = (r * 3 + c * 7) % 10;
            else if (mode == 2) v = (r * 5 + c * 3 + (r * c) % 7) % 10;
            else v = (r * 9 + c * 4 + (r + 1) * (c + 2)) % 10;
            st.cell[r * W + c] = (uint8_t)v;
        }
    }
    rebuildMasks(st);
    return st;
}

static State makeRandomState(mt19937& rng) {
    State st;
    array<int, 10> cnt{};
    uniform_int_distribution<int> dig(0, 9);
    for (int i = 0; i < N; ++i) {
        st.cell[i] = (uint8_t)dig(rng);
        cnt[st.cell[i]]++;
    }

    const int minCnt = 7;
    vector<int> idxs(N);
    iota(idxs.begin(), idxs.end(), 0);
    shuffle(idxs.begin(), idxs.end(), rng);

    int ptr = 0;
    for (int d = 0; d < 10; ++d) {
        while (cnt[d] < minCnt) {
            if (ptr >= N) ptr = 0;
            int i = idxs[ptr++];
            int od = st.cell[i];
            if (od == d) continue;
            st.cell[i] = (uint8_t)d;
            cnt[od]--;
            cnt[d]++;
        }
    }

    rebuildMasks(st);

    // Ensure each digit has at least one adjacent pair if possible by forcing a random neighbor pair.
    uniform_int_distribution<int> posdist(0, N - 1);
    for (int d = 0; d < 10; ++d) {
        if (hasAdjPairDigit(st, d)) continue;
        int tries = 200;
        while (tries--) {
            int i = posdist(rng);
            Bits nb = neighMask[i];
            vector<int> neighs;
            uint64_t x = nb.w0;
            while (x) {
                int b = __builtin_ctzll(x);
                neighs.push_back(b);
                x &= x - 1;
            }
            x = nb.w1;
            while (x) {
                int b = __builtin_ctzll(x);
                int j = 64 + b;
                if (j < N) neighs.push_back(j);
                x &= x - 1;
            }
            if (neighs.empty()) continue;
            int j = neighs[uniform_int_distribution<int>(0, (int)neighs.size() - 1)(rng)];
            setDigit(st, i, (uint8_t)d);
            setDigit(st, j, (uint8_t)d);
            if (hasAdjPairDigit(st, d)) break;
        }
    }

    return st;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute adjacency (8 directions)
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int i = r * W + c;
            Bits m{};
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr, nc = c + dc;
                    if (0 <= nr && nr < H && 0 <= nc && nc < W) {
                        int j = nr * W + nc;
                        setBit(m, j);
                    }
                }
            }
            neighMask[i] = m;
        }
    }

    // Precompute digit sequences for numbers
    numDigits.assign(MAXCHECK + 2, {});
    for (int n = 1; n <= MAXCHECK + 1; ++n) {
        string s = to_string(n);
        numDigits[n].reserve(s.size());
        for (char ch : s) numDigits[n].push_back((uint8_t)(ch - '0'));
    }

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto t0 = chrono::steady_clock::now();
    const double timeLimitSec = 10.0;

    State best = makePatternState(0);
    int bestScore = evalFull(best);

    // Seed candidates
    for (int mode = 1; mode <= 3; ++mode) {
        State st = makePatternState(mode);
        int sc = evalFull(st);
        if (sc > bestScore) { bestScore = sc; best = st; }
    }

    // Random sampling phase (~20% time)
    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        if (elapsed > timeLimitSec * 0.2) break;
        State st = makeRandomState(rng);
        int sc = evalFull(st);
        if (sc > bestScore) { bestScore = sc; best = st; }
    }

    // Simulated annealing phase
    State cur = best;
    int curScore = bestScore;

    uniform_int_distribution<int> posdist(0, N - 1);
    uniform_int_distribution<int> digdist(0, 9);
    uniform_real_distribution<double> u01(0.0, 1.0);

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        if (elapsed > timeLimitSec) break;
        double prog = min(1.0, elapsed / timeLimitSec);
        double T = 5.0 + (0.15 - 5.0) * prog; // linear cooling
        if (T < 0.15) T = 0.15;

        bool doSwap = (u01(rng) < 0.30);
        int i = posdist(rng), j = posdist(rng);
        uint8_t oldi = cur.cell[i], oldj = cur.cell[j];
        uint8_t nd = (uint8_t)digdist(rng);

        if (!doSwap) {
            if (nd == oldi) continue;
            setDigit(cur, i, nd);
        } else {
            if (i == j) continue;
            swapDigits(cur, i, j);
        }

        int limit = min(MAXCHECK, curScore + 1);
        int s = evalUpTo(cur, limit);
        int newScore = (s < limit ? s : evalContinue(cur, limit));

        int delta = newScore - curScore;
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double p = exp((double)delta / T);
            accept = (u01(rng) < p);
        }

        if (accept) {
            curScore = newScore;
            if (curScore > bestScore) {
                bestScore = curScore;
                best = cur;
            }
            // occasional random kick if stuck
            if (u01(rng) < 0.002) {
                State kick = makeRandomState(rng);
                int sc = evalFull(kick);
                if (sc >= curScore) { cur = kick; curScore = sc; }
                if (sc > bestScore) { bestScore = sc; best = kick; }
            }
        } else {
            // undo
            if (!doSwap) {
                setDigit(cur, i, oldi);
            } else {
                // swap back
                swapDigits(cur, i, j);
            }
        }
    }

    // Output best grid
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            uint8_t d = best.cell[r * W + c];
            char ch = char('0' + d);
            cout << ch;
        }
        cout << '\n';
    }
    return 0;
}