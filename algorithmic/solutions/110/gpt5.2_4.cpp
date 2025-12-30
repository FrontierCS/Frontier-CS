#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed = 1) : x(seed) {}
    static uint64_t splitmix64(uint64_t &s) {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint64_t nextU64() { return splitmix64(x); }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    inline double nextDouble() {
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0); // [0,1)
    }
};

static constexpr int H = 8, W = 14, N = H * W;
static constexpr int MAX_CHECK = 200000;

struct Mask {
    uint64_t a = 0, b = 0; // bits [0..63], [64..127]
    inline bool empty() const { return a == 0 && b == 0; }
};

static inline void setBit(Mask &m, int idx) {
    if (idx < 64) m.a |= (1ULL << idx);
    else m.b |= (1ULL << (idx - 64));
}
static inline void clrBit(Mask &m, int idx) {
    if (idx < 64) m.a &= ~(1ULL << idx);
    else m.b &= ~(1ULL << (idx - 64));
}

struct NumRep {
    uint8_t len = 0;
    uint8_t d[6]{};
};

static array<NumRep, MAX_CHECK + 1> nums;
static array<vector<int>, N> neigh;

struct Grid {
    array<uint8_t, N> dig{};
    array<int, 10> cnt{};
    array<Mask, 10> nodes{};
    array<array<Mask, 10>, N> trans{};

    void build() {
        cnt.fill(0);
        for (int d = 0; d < 10; d++) nodes[d] = Mask{};
        for (int v = 0; v < N; v++) for (int d = 0; d < 10; d++) trans[v][d] = Mask{};

        for (int i = 0; i < N; i++) {
            cnt[dig[i]]++;
            setBit(nodes[dig[i]], i);
        }
        for (int v = 0; v < N; v++) {
            for (int u : neigh[v]) {
                setBit(trans[v][dig[u]], u);
            }
        }
    }

    inline void setDigitNoCheck(int i, uint8_t nd) {
        uint8_t od = dig[i];
        if (od == nd) return;
        cnt[od]--; cnt[nd]++;
        clrBit(nodes[od], i);
        setBit(nodes[nd], i);
        for (int u : neigh[i]) {
            clrBit(trans[u][od], i);
            setBit(trans[u][nd], i);
        }
        dig[i] = nd;
    }

    inline void swapCells(int i, int j) {
        uint8_t di = dig[i], dj = dig[j];
        if (di == dj) return;

        clrBit(nodes[di], i);
        setBit(nodes[dj], i);
        clrBit(nodes[dj], j);
        setBit(nodes[di], j);

        for (int u : neigh[i]) {
            clrBit(trans[u][di], i);
            setBit(trans[u][dj], i);
        }
        for (int u : neigh[j]) {
            clrBit(trans[u][dj], j);
            setBit(trans[u][di], j);
        }

        dig[i] = dj;
        dig[j] = di;
    }

    inline bool canRead(const NumRep &nr) const {
        uint8_t first = nr.d[0];
        Mask cur = nodes[first];
        if (cur.empty()) return false;

        for (int pos = 1; pos < nr.len; pos++) {
            uint8_t want = nr.d[pos];
            Mask nxt{};
            uint64_t w = cur.a;
            while (w) {
                int b = __builtin_ctzll(w);
                int v = b;
                const Mask &m = trans[v][want];
                nxt.a |= m.a; nxt.b |= m.b;
                w &= (w - 1);
            }
            w = cur.b;
            while (w) {
                int b = __builtin_ctzll(w);
                int v = 64 + b;
                const Mask &m = trans[v][want];
                nxt.a |= m.a; nxt.b |= m.b;
                w &= (w - 1);
            }
            cur = nxt;
            if (cur.empty()) return false;
        }
        return true;
    }

    inline int score() const {
        for (int x = 1; x <= MAX_CHECK; x++) {
            if (!canRead(nums[x])) return x - 1;
        }
        return MAX_CHECK;
    }
};

struct Mutation {
    int type = 0; // 1 change, 2 swap
    int i = -1, j = -1;
    uint8_t oldd = 0, newd = 0;
};

static void precomputeNums() {
    nums[0].len = 1;
    nums[0].d[0] = 0;
    for (int i = 1; i <= MAX_CHECK; i++) {
        int x = i;
        uint8_t tmp[6];
        int len = 0;
        while (x > 0) {
            tmp[len++] = (uint8_t)(x % 10);
            x /= 10;
        }
        nums[i].len = (uint8_t)len;
        for (int k = 0; k < len; k++) nums[i].d[k] = tmp[len - 1 - k];
    }
}

static void buildNeighbors() {
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int v = r * W + c;
            neigh[v].clear();
            for (int dr = -1; dr <= 1; dr++) {
                for (int dc = -1; dc <= 1; dc++) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr, nc = c + dc;
                    if (0 <= nr && nr < H && 0 <= nc && nc < W) {
                        neigh[v].push_back(nr * W + nc);
                    }
                }
            }
        }
    }
}

static void shuffleVec(vector<uint8_t> &a, RNG &rng) {
    for (int i = (int)a.size() - 1; i > 0; i--) {
        int j = rng.nextInt(i + 1);
        swap(a[i], a[j]);
    }
}

static void initRandomGrid(Grid &g, RNG &rng) {
    vector<uint8_t> pool;
    pool.reserve(N);
    for (int d = 0; d < 10; d++) for (int k = 0; k < 11; k++) pool.push_back((uint8_t)d);
    while ((int)pool.size() < N) pool.push_back((uint8_t)rng.nextInt(10));
    shuffleVec(pool, rng);
    for (int i = 0; i < N; i++) g.dig[i] = pool[i];
    g.build();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    precomputeNums();
    buildNeighbors();

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 7) ^ (seed >> 9) ^ 0x9e3779b97f4a7c15ULL;
    RNG rng(seed);

    Grid cur;
    initRandomGrid(cur, rng);
    int curScore = cur.score();
    array<uint8_t, N> bestDig = cur.dig;
    int bestScore = curScore;

    vector<uint8_t> failDigits;
    auto updateFailDigits = [&](int score) {
        failDigits.clear();
        int fail = score + 1;
        if (1 <= fail && fail <= MAX_CHECK) {
            const auto &nr = nums[fail];
            failDigits.assign(nr.d, nr.d + nr.len);
        }
    };
    updateFailDigits(curScore);

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 54.0;
    int stepsSinceBest = 0;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed >= TIME_LIMIT_SEC) break;
        double frac = min(1.0, elapsed / TIME_LIMIT_SEC);
        double T = 5.0 * (1.0 - frac) + 0.15;

        Mutation mut;
        bool doSwap = (rng.nextInt(100) < 55);

        if (doSwap) {
            int i = rng.nextInt(N);
            int j = rng.nextInt(N - 1);
            if (j >= i) j++;
            if (cur.dig[i] == cur.dig[j]) continue;
            mut.type = 2; mut.i = i; mut.j = j;
            cur.swapCells(i, j);
        } else {
            int i = rng.nextInt(N);
            uint8_t od = cur.dig[i];
            if (cur.cnt[od] <= 1) continue;

            uint8_t nd = od;
            for (int tries = 0; tries < 20 && nd == od; tries++) {
                if (!failDigits.empty() && rng.nextInt(100) < 70) nd = failDigits[rng.nextInt((int)failDigits.size())];
                else nd = (uint8_t)rng.nextInt(10);
            }
            if (nd == od) nd = (uint8_t)((od + 1 + rng.nextInt(9)) % 10);

            mut.type = 1; mut.i = i; mut.oldd = od; mut.newd = nd;
            cur.setDigitNoCheck(i, nd);
        }

        int newScore = cur.score();
        int delta = newScore - curScore;
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double p = exp((double)delta / T);
            accept = (rng.nextDouble() < p);
        }

        if (accept) {
            curScore = newScore;
            updateFailDigits(curScore);
            if (newScore > bestScore) {
                bestScore = newScore;
                bestDig = cur.dig;
                stepsSinceBest = 0;
            } else {
                stepsSinceBest++;
            }
        } else {
            if (mut.type == 1) {
                cur.setDigitNoCheck(mut.i, mut.oldd);
            } else {
                cur.swapCells(mut.i, mut.j);
            }
            stepsSinceBest++;
        }

        if (stepsSinceBest > 800) {
            Grid ng;
            initRandomGrid(ng, rng);
            int sc = ng.score();
            cur = std::move(ng);
            curScore = sc;
            updateFailDigits(curScore);
            stepsSinceBest = 0;
            if (curScore > bestScore) {
                bestScore = curScore;
                bestDig = cur.dig;
            }
        }
    }

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            cout << char('0' + bestDig[r * W + c]);
        }
        cout << '\n';
    }
    return 0;
}