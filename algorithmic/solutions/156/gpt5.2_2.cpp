#include <bits/stdc++.h>
using namespace std;

static constexpr int H = 30, W = 30;
static constexpr int C = H * W;
static constexpr int D = 4;
static constexpr int NODES = C * D;

static constexpr int di[D] = {0, -1, 0, 1};
static constexpr int dj[D] = {-1, 0, 1, 0};

// to[t][d]: when entering a tile of type t from direction d (0:L,1:U,2:R,3:D),
// the direction to leave the tile, or -1 if cannot enter.
static constexpr int8_t toDir[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int l, int r) { // inclusive
        return l + (int)(nextU64() % (uint64_t)(r - l + 1));
    }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

static inline int rotType(int t, int r) {
    r &= 3;
    if (t <= 3) return (t + r) & 3;
    if (t == 4 || t == 5) return ((r & 1) ? (t ^ 1) : t);
    if (t == 6 || t == 7) return ((r & 1) ? (t ^ 1) : t);
    return t;
}

struct EvalRes {
    int top1 = 0;
    int top2 = 0;
    int cycles = 0;
    int sumCycles = 0;
    int score = 0; // objective: L1*L2 or 0 if cycles<=1
    int value = 0; // search value
};

struct Evaluator {
    int nnode[C][D]; // neighbor node id given out direction (0..3), or -1 if OOB
    int nextNode[NODES];
    uint8_t invalidEntry[NODES];
    uint8_t vis[NODES];
    int pos[NODES];
    int st[NODES];

    Evaluator() {
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                int c = i * W + j;
                for (int out = 0; out < D; out++) {
                    int ni = i + di[out], nj = j + dj[out];
                    if (0 <= ni && ni < H && 0 <= nj && nj < W) {
                        int c2 = ni * W + nj;
                        int nd = (out + 2) & 3;
                        nnode[c][out] = c2 * 4 + nd;
                    } else {
                        nnode[c][out] = -1;
                    }
                }
            }
        }
    }

    inline EvalRes eval(const int type[C]) {
        // build transitions
        for (int c = 0; c < C; c++) {
            int t = type[c];
            int base = c * 4;
            for (int d = 0; d < 4; d++) {
                int v = base + d;
                int d2 = toDir[t][d];
                if (d2 == -1) {
                    invalidEntry[v] = 1;
                    nextNode[v] = -1;
                } else {
                    invalidEntry[v] = 0;
                    int nn = nnode[c][d2];
                    if (nn == -1) {
                        nextNode[v] = -1;
                    } else {
                        int c2 = nn >> 2;
                        int nd = nn & 3;
                        int t2 = type[c2];
                        if (toDir[t2][nd] == -1) nextNode[v] = -1;
                        else nextNode[v] = nn;
                    }
                }
            }
        }

        // init arrays
        memset(vis, 0, sizeof(vis));
        for (int i = 0; i < NODES; i++) pos[i] = -1;

        EvalRes res;
        for (int v0 = 0; v0 < NODES; v0++) {
            if (invalidEntry[v0] || vis[v0]) continue;
            int u = v0;
            int len = 0;

            while (u != -1 && !invalidEntry[u] && !vis[u] && pos[u] == -1) {
                pos[u] = len;
                st[len++] = u;
                u = nextNode[u];
            }

            if (u != -1 && !invalidEntry[u] && !vis[u] && pos[u] != -1) {
                int cycLen = len - pos[u];
                res.cycles++;
                res.sumCycles += cycLen;
                if (cycLen > res.top1) {
                    res.top2 = res.top1;
                    res.top1 = cycLen;
                } else if (cycLen == res.top1) {
                    if (res.top2 < res.top1) res.top2 = res.top1;
                } else if (cycLen > res.top2) {
                    res.top2 = cycLen;
                }
            }

            for (int k = 0; k < len; k++) {
                int x = st[k];
                vis[x] = 1;
                pos[x] = -1;
            }
        }

        if (res.cycles >= 2) res.score = res.top1 * res.top2;
        else res.score = 0;

        // auxiliary value to escape 0-score plateaus
        res.value = res.score + 100 * res.top1 + 10 * res.top2 + res.sumCycles;
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    array<int, C> initType{};
    for (int i = 0; i < H; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < W; j++) initType[i * W + j] = s[j] - '0';
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 7) ^ (seed >> 9) ^ 0x9e3779b97f4a7c15ULL;
    XorShift64 rng(seed);

    Evaluator ev;

    array<int, C> rot{}, type{};
    auto applyAll = [&]() {
        for (int c = 0; c < C; c++) type[c] = rotType(initType[c], rot[c]);
    };

    // random initial sampling
    array<int, C> bestRot{};
    int bestScore = -1;
    EvalRes bestER;

    int samples = 20;
    for (int s = 0; s < samples; s++) {
        for (int c = 0; c < C; c++) rot[c] = rng.nextInt(0, 3);
        applyAll();
        EvalRes er = ev.eval(type.data());
        if (er.score > bestScore) {
            bestScore = er.score;
            bestER = er;
            bestRot = rot;
        }
    }

    // start from best sampled
    rot = bestRot;
    applyAll();
    EvalRes curER = ev.eval(type.data());

    // SA
    const double TL = 1.90;
    const double T0 = 2000.0;
    const double T1 = 5.0;

    auto start = chrono::steady_clock::now();
    int iter = 0;
    while (true) {
        if ((iter & 255) == 0) {
            double t = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (t >= TL) break;
        }
        iter++;

        int c = rng.nextInt(0, C - 1);
        int oldr = rot[c];
        int k = rng.nextInt(1, 3);
        int newr = (oldr + k) & 3;

        rot[c] = newr;
        int oldType = type[c];
        type[c] = rotType(initType[c], newr);

        EvalRes newER = ev.eval(type.data());
        int delta = newER.value - curER.value;

        double t = chrono::duration<double>(chrono::steady_clock::now() - start).count() / TL;
        if (t > 1.0) t = 1.0;
        double temp = T0 * pow(T1 / T0, t);

        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp((double)delta / temp);
            if (rng.nextDouble() < prob) accept = true;
        }

        if (accept) {
            curER = newER;
            if (newER.score > bestScore) {
                bestScore = newER.score;
                bestER = newER;
                bestRot = rot;
            }
        } else {
            rot[c] = oldr;
            type[c] = oldType;
        }
    }

    // output best rotations
    string out;
    out.reserve(C);
    for (int c = 0; c < C; c++) out.push_back(char('0' + bestRot[c]));
    cout << out << "\n";
    return 0;
}