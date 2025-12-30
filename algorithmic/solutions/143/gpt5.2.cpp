#include <bits/stdc++.h>
using namespace std;

struct XorShift128Plus {
    uint64_t s[2];

    static uint64_t splitmix64(uint64_t &x) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }

    explicit XorShift128Plus(uint64_t seed = 0x123456789abcdefULL) {
        uint64_t x = seed;
        s[0] = splitmix64(x);
        s[1] = splitmix64(x);
        if (s[0] == 0 && s[1] == 0) s[1] = 1;
    }

    inline uint64_t nextU64() {
        uint64_t x = s[0];
        uint64_t y = s[1];
        s[0] = y;
        x ^= x << 23;
        x ^= x >> 17;
        x ^= y ^ (y >> 26);
        s[1] = x;
        return x + y;
    }

    inline uint32_t nextU32() { return (uint32_t)nextU64(); }

    inline int nextInt(int n) { // n > 0
        return (int)(nextU64() % (uint64_t)n);
    }

    inline double nextDouble() {
        // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

static int COMB[21][5];
static int COMB_CNT = 0;

static inline void initCombs() {
    COMB_CNT = 0;
    for (int a = 0; a < 7; a++)
        for (int b = a + 1; b < 7; b++)
            for (int c = b + 1; c < 7; c++)
                for (int d = c + 1; d < 7; d++)
                    for (int e = d + 1; e < 7; e++) {
                        COMB[COMB_CNT][0] = a;
                        COMB[COMB_CNT][1] = b;
                        COMB[COMB_CNT][2] = c;
                        COMB[COMB_CNT][3] = d;
                        COMB[COMB_CNT][4] = e;
                        COMB_CNT++;
                    }
}

static inline uint64_t eval5(const int *c) {
    int suitCnt[4] = {0, 0, 0, 0};
    int cnt[15] = {0};
    uint16_t mask = 0;

    for (int i = 0; i < 5; i++) {
        int id = c[i];
        int r = (id % 13) + 2;   // 2..14
        int s = id / 13;         // 0..3
        suitCnt[s]++;
        cnt[r]++;
        mask |= (uint16_t)(1u << (r - 2));
    }

    bool flush = (suitCnt[0] == 5 || suitCnt[1] == 5 || suitCnt[2] == 5 || suitCnt[3] == 5);

    int straightHigh = 0;
    if (__builtin_popcount((unsigned)mask) == 5) {
        const uint16_t wheel = (uint16_t)((1u << 12) | (1u << 0) | (1u << 1) | (1u << 2) | (1u << 3)); // A,2,3,4,5
        if (mask == wheel) {
            straightHigh = 5;
        } else {
            for (int high = 14; high >= 6; --high) {
                uint16_t pat = (uint16_t)(0x1Fu << (high - 6));
                if (mask == pat) {
                    straightHigh = high;
                    break;
                }
            }
        }
    }

    struct Item { int c, r; };
    Item items[5];
    int d = 0;
    int maxCnt = 0;

    for (int r = 14; r >= 2; --r) {
        if (cnt[r]) {
            items[d++] = {cnt[r], r};
            if (cnt[r] > maxCnt) maxCnt = cnt[r];
        }
    }

    for (int i = 0; i < d; i++) {
        for (int j = i + 1; j < d; j++) {
            if (items[j].c > items[i].c || (items[j].c == items[i].c && items[j].r > items[i].r)) {
                swap(items[i], items[j]);
            }
        }
    }

    int seq[5] = {0, 0, 0, 0, 0};
    int idx = 0;
    for (int i = 0; i < d; i++) {
        for (int t = 0; t < items[i].c; t++) seq[idx++] = items[i].r;
    }

    int cat = 0;
    if (straightHigh && flush) {
        cat = 8;
        seq[0] = straightHigh; seq[1] = seq[2] = seq[3] = seq[4] = 0;
    } else if (maxCnt == 4) {
        cat = 7;
    } else if (maxCnt == 3 && d == 2) {
        cat = 6;
    } else if (flush) {
        cat = 5;
    } else if (straightHigh) {
        cat = 4;
        seq[0] = straightHigh; seq[1] = seq[2] = seq[3] = seq[4] = 0;
    } else if (maxCnt == 3) {
        cat = 3;
    } else if (maxCnt == 2 && d == 3) {
        cat = 2;
    } else if (maxCnt == 2) {
        cat = 1;
    } else {
        cat = 0;
    }

    uint64_t key = (uint64_t)cat << 20;
    key |= (uint64_t)(seq[0] & 0xF) << 16;
    key |= (uint64_t)(seq[1] & 0xF) << 12;
    key |= (uint64_t)(seq[2] & 0xF) << 8;
    key |= (uint64_t)(seq[3] & 0xF) << 4;
    key |= (uint64_t)(seq[4] & 0xF);
    return key;
}

static inline uint64_t eval7(const int *c7) {
    uint64_t best = 0;
    int h[5];
    for (int t = 0; t < 21; t++) {
        h[0] = c7[COMB[t][0]];
        h[1] = c7[COMB[t][1]];
        h[2] = c7[COMB[t][2]];
        h[3] = c7[COMB[t][3]];
        h[4] = c7[COMB[t][4]];
        uint64_t k = eval5(h);
        if (k > best) best = k;
    }
    return best;
}

struct Equity {
    double w = 0.0;
    double d = 0.0;
};

static inline Equity equityRiverExact(const int hole[2], const int board5[5]) {
    uint64_t usedMask = 0;
    usedMask |= (1ULL << hole[0]);
    usedMask |= (1ULL << hole[1]);
    for (int i = 0; i < 5; i++) usedMask |= (1ULL << board5[i]);

    int rem[52];
    int n = 0;
    for (int c = 0; c < 52; c++) {
        if (((usedMask >> c) & 1ULL) == 0) rem[n++] = c;
    }

    int our7[7] = {hole[0], hole[1], board5[0], board5[1], board5[2], board5[3], board5[4]};
    uint64_t ourKey = eval7(our7);

    long long win = 0, tie = 0;
    long long total = 0;
    int bob7[7] = {0, 0, board5[0], board5[1], board5[2], board5[3], board5[4]};

    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            bob7[0] = rem[i];
            bob7[1] = rem[j];
            uint64_t bobKey = eval7(bob7);
            if (ourKey > bobKey) win++;
            else if (ourKey == bobKey) tie++;
            total++;
        }
    }

    Equity e;
    e.w = (double)win / (double)total;
    e.d = (double)tie / (double)total;
    return e;
}

static inline Equity equityMonteCarlo(const int hole[2], const int *board, int k, int trials, XorShift128Plus &rng) {
    uint64_t usedMask = 0;
    usedMask |= (1ULL << hole[0]);
    usedMask |= (1ULL << hole[1]);
    for (int i = 0; i < k; i++) usedMask |= (1ULL << board[i]);

    int rem[52];
    int n = 0;
    for (int c = 0; c < 52; c++) {
        if (((usedMask >> c) & 1ULL) == 0) rem[n++] = c;
    }

    int need = 2 + (5 - k);
    int swapIdx[7];

    int fullBoard[5];
    for (int i = 0; i < k; i++) fullBoard[i] = board[i];

    int our7[7], bob7[7];
    long long win = 0, tie = 0;

    for (int t = 0; t < trials; t++) {
        for (int i = 0; i < need; i++) {
            int j = i + rng.nextInt(n - i);
            swap(rem[i], rem[j]);
            swapIdx[i] = j;
        }

        int bob0 = rem[0], bob1 = rem[1];
        for (int i = k; i < 5; i++) fullBoard[i] = rem[2 + (i - k)];

        our7[0] = hole[0]; our7[1] = hole[1];
        bob7[0] = bob0;    bob7[1] = bob1;
        for (int i = 0; i < 5; i++) {
            our7[2 + i] = fullBoard[i];
            bob7[2 + i] = fullBoard[i];
        }

        uint64_t ourKey = eval7(our7);
        uint64_t bobKey = eval7(bob7);
        if (ourKey > bobKey) win++;
        else if (ourKey == bobKey) tie++;

        for (int i = need - 1; i >= 0; i--) {
            int j = swapIdx[i];
            swap(rem[i], rem[j]);
        }
    }

    Equity e;
    e.w = (double)win / (double)trials;
    e.d = (double)tie / (double)trials;
    return e;
}

static inline int clampBet(long long x, int a) {
    if (a <= 0) return 0;
    if (x < 1) x = 1;
    if (x > a) x = a;
    return (int)x;
}

static inline int chooseBet(int round, int a, int P, int k, double e, uint64_t ourKey, XorShift128Plus &rng) {
    if (a <= 0) return 0;

    if (k < 5) {
        if (round == 1) {
            if (e > 0.72) return clampBet(12, a);
            if (e > 0.64) return clampBet(8, a);
            if (e > 0.58) return clampBet(4, a);
            return 0;
        } else if (round == 2) {
            if (e > 0.80) return clampBet(max(6, P), a);
            if (e > 0.70) return clampBet(max(4, P / 2), a);
            if (e > 0.60) return clampBet(max(2, P / 3), a);
            return 0;
        } else { // round 3
            if (e > 0.84) return clampBet(max<long long>(P, a / 2), a);
            if (e > 0.74) return clampBet(max<long long>(P * 2LL / 3LL, 6LL), a);
            if (e > 0.64) return clampBet(max<long long>(P / 2LL, 4LL), a);
            if (e > 0.56) return clampBet(max<long long>(P / 3LL, 2LL), a);
            return 0;
        }
    } else {
        int cat = (int)(ourKey >> 20);

        if (cat >= 7 && e > 0.70) return a;
        if (cat == 6 && e > 0.82) return a;

        if (e >= 0.85) return a;
        if (e >= 0.75) return clampBet(max<long long>(P, a / 2), a);
        if (e >= 0.65) return clampBet(P, a);
        if (e >= 0.58) return clampBet(max<long long>(2, P / 2), a);
        if (e >= 0.52) return clampBet(max<long long>(1, P / 3), a);

        // Bluffs (river only), pot must be large enough
        if (P >= 20 && e < 0.50) {
            double p;
            if (e <= 0.20) p = 0.45;
            else if (e <= 0.30) p = 0.32;
            else if (e <= 0.40) p = 0.20;
            else p = 0.10;

            if (rng.nextDouble() < p) {
                long long desired = P;
                if (e <= 0.18 && P >= 40) desired = (long long)(P * 3LL / 2LL);
                if (desired < 1) desired = 1;
                return clampBet(desired, a);
            }
        }
        return 0;
    }
}

static inline int toCardId(int suit, int valLabel) {
    // valLabel: 1..13 for 2..A
    return suit * 13 + (valLabel - 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    initCombs();
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    XorShift128Plus rng(seed);

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    string tok;
    for (int hand = 1; hand <= G; hand++) {
        bool hasTok = false;
        while (true) {
            if (!hasTok) {
                if (!(cin >> tok)) return 0;
            } else {
                hasTok = false;
            }

            if (tok == "-1") return 0;
            if (tok == "SCORE") {
                double W;
                cin >> W;
                return 0;
            }
            if (tok != "STATE") return 0;

            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            cin >> tok;
            if (tok == "-1") return 0;
            if (tok != "ALICE") return 0;
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
            int hole[2] = {toCardId(s1, v1), toCardId(s2, v2)};

            cin >> tok;
            if (tok == "-1") return 0;
            if (tok != "BOARD") return 0;
            int board[5];
            for (int i = 0; i < k; i++) {
                int ss, vv;
                cin >> ss >> vv;
                board[i] = toCardId(ss, vv);
            }

            double w = 0.0, d = 0.0;
            uint64_t ourKey = 0;

            if (k == 5) {
                Equity eq = equityRiverExact(hole, board);
                w = eq.w;
                d = eq.d;
                int our7[7] = {hole[0], hole[1], board[0], board[1], board[2], board[3], board[4]};
                ourKey = eval7(our7);
            } else {
                int trials;
                if (k == 0) trials = 130;
                else if (k == 3) trials = 160;
                else trials = 210; // k == 4

                if (k == 4 && P >= 60) trials += 80;
                if (k == 3 && P >= 50) trials += 60;
                if (k == 0 && P >= 30) trials += 40;

                Equity eq = equityMonteCarlo(hole, board, k, trials, rng);
                w = eq.w;
                d = eq.d;
            }

            double e = w + 0.5 * d;
            int bet = chooseBet(r, a, P, k, e, ourKey, rng);

            if (bet <= 0) {
                cout << "ACTION CHECK" << endl;
            } else {
                cout << "ACTION RAISE " << bet << endl;
            }

            // Read opponent response
            if (!(cin >> tok)) return 0;
            if (tok == "-1") return 0;
            if (tok != "OPP") return 0;
            string resp;
            cin >> resp;
            if (resp == "-1") return 0;
            if (resp == "CALL") {
                int x;
                cin >> x;
            } else if (resp == "FOLD") {
                // nothing
            } else if (resp == "CHECK") {
                // nothing
            } else {
                return 0;
            }

            // Next token: RESULT or STATE
            if (!(cin >> tok)) return 0;
            if (tok == "-1") return 0;
            if (tok == "RESULT") {
                int delta;
                cin >> delta;
                break;
            } else if (tok == "STATE") {
                hasTok = true;
                continue;
            } else if (tok == "SCORE") {
                double W;
                cin >> W;
                return 0;
            } else {
                return 0;
            }
        }
    }

    if (cin >> tok) {
        if (tok == "-1") return 0;
        if (tok == "SCORE") {
            double W;
            cin >> W;
        }
    }
    return 0;
}