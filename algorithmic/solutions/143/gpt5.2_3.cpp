#include <bits/stdc++.h>
using namespace std;

struct Card {
    uint8_t s; // 0..3
    uint8_t v; // 2..14
};

static inline int cardId(const Card& c) { return (int)c.s * 13 + (int)c.v - 2; }

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0x123456789abcdefULL) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32(uint32_t mod) { return (uint32_t)(next() % mod); }
};

static array<Card, 52> DECK;
static array<array<int,5>, 21> COMBOS;

static inline uint64_t packSeq(const int seq[5]) {
    uint64_t p = 0;
    for (int i = 0; i < 5; i++) p = p * 15ULL + (uint64_t)seq[i];
    return p;
}

static inline uint64_t eval5Idx(const array<Card,7>& c, const array<int,5>& idx) {
    int cnt[15];
    int suitCnt[4];
    memset(cnt, 0, sizeof(cnt));
    memset(suitCnt, 0, sizeof(suitCnt));

    int mask = 0;
    for (int i = 0; i < 5; i++) {
        const Card& cd = c[idx[i]];
        cnt[cd.v]++;
        suitCnt[cd.s]++;
        mask |= (1 << (cd.v - 2));
    }

    bool flush = false;
    for (int s = 0; s < 4; s++) if (suitCnt[s] == 5) { flush = true; break; }

    bool straight = false;
    int straightHigh = 0;
    if (__builtin_popcount((unsigned)mask) == 5) {
        if (mask == 0x100F) { // A,2,3,4,5
            straight = true;
            straightHigh = 5;
        } else {
            int low = __builtin_ctz((unsigned)mask);
            if (mask == (0x1F << low)) {
                straight = true;
                straightHigh = (low + 2 + 4);
            }
        }
    }

    // multiplicities
    pair<int,int> mv[5];
    int m = 0;
    for (int v = 14; v >= 2; v--) { // iterate high->low to help stable ordering
        if (cnt[v]) mv[m++] = {cnt[v], v};
    }
    // sort by multiplicity desc, value desc
    for (int i = 0; i < m; i++) {
        for (int j = i + 1; j < m; j++) {
            if (mv[j].first > mv[i].first || (mv[j].first == mv[i].first && mv[j].second > mv[i].second)) {
                swap(mv[i], mv[j]);
            }
        }
    }

    int seq[5];
    int pos = 0;
    for (int i = 0; i < m; i++) {
        for (int t = 0; t < mv[i].first; t++) seq[pos++] = mv[i].second;
    }

    int cat;
    if (straight && flush) cat = 8;
    else if (mv[0].first == 4) cat = 7;
    else if (mv[0].first == 3 && m >= 2 && mv[1].first == 2) cat = 6;
    else if (flush) cat = 5;
    else if (straight) cat = 4;
    else if (mv[0].first == 3) cat = 3;
    else if (mv[0].first == 2 && m >= 2 && mv[1].first == 2) cat = 2;
    else if (mv[0].first == 2) cat = 1;
    else cat = 0;

    uint64_t key = ((uint64_t)cat << 32);
    if (cat == 8 || cat == 4) key |= (uint64_t)straightHigh;
    else key |= packSeq(seq);
    return key;
}

static inline uint64_t eval7(const array<Card,7>& c) {
    uint64_t best = 0;
    for (int i = 0; i < 21; i++) {
        uint64_t k = eval5Idx(c, COMBOS[i]);
        if (k > best) best = k;
    }
    return best;
}

struct Equity {
    double win = 0.0;
    double tie = 0.0;
};

static Equity estimateEquity(const Card hole[2], const vector<Card>& board, int samples, SplitMix64& rng) {
    bool used[52];
    memset(used, 0, sizeof(used));
    used[cardId(hole[0])] = true;
    used[cardId(hole[1])] = true;
    for (auto &bc : board) used[cardId(bc)] = true;

    int remIds[52];
    int n = 0;
    for (int id = 0; id < 52; id++) if (!used[id]) remIds[n++] = id;

    int k = (int)board.size();
    int needBoard = 5 - k;
    int need = 2 + needBoard;

    array<Card,7> a7, b7;
    a7[0] = hole[0];
    a7[1] = hole[1];

    Card fullBoard[5];
    for (int i = 0; i < k; i++) fullBoard[i] = board[i];

    bool myFixed = (needBoard == 0);
    uint64_t myKeyFixed = 0;
    if (myFixed) {
        for (int i = 0; i < 5; i++) a7[2 + i] = fullBoard[i];
        myKeyFixed = eval7(a7);
    }

    int w = 0, t = 0;
    int chosen[7];

    for (int it = 0; it < samples; it++) {
        for (int i = 0; i < need; i++) {
            while (true) {
                int idx = (int)rng.nextU32((uint32_t)n);
                bool ok = true;
                for (int j = 0; j < i; j++) if (chosen[j] == idx) { ok = false; break; }
                if (ok) { chosen[i] = idx; break; }
            }
        }

        Card bob0 = DECK[remIds[chosen[0]]];
        Card bob1 = DECK[remIds[chosen[1]]];
        for (int i = 0; i < needBoard; i++) fullBoard[k + i] = DECK[remIds[chosen[2 + i]]];

        b7[0] = bob0; b7[1] = bob1;
        for (int i = 0; i < 5; i++) b7[2 + i] = fullBoard[i];

        uint64_t myKey;
        if (myFixed) {
            myKey = myKeyFixed;
        } else {
            for (int i = 0; i < 5; i++) a7[2 + i] = fullBoard[i];
            myKey = eval7(a7);
        }
        uint64_t bobKey = eval7(b7);

        if (myKey > bobKey) w++;
        else if (myKey == bobKey) t++;
    }

    Equity e;
    e.win = (double)w / (double)samples;
    e.tie = (double)t / (double)samples;
    return e;
}

static inline bool preflopCandidate(const Card& c1, const Card& c2) {
    int r1 = c1.v, r2 = c2.v;
    bool suited = (c1.s == c2.s);
    int hi = max(r1, r2), lo = min(r1, r2);
    if (r1 == r2) return r1 >= 8; // 88+
    if (hi >= 14 && lo >= 10) return true; // AK..AT
    if (hi >= 13 && lo >= 10) return true; // KQ, KJ, KT, AQ..
    if (hi >= 12 && lo >= 10) return suited; // suited QTs+
    if (hi >= 12 && lo >= 9 && suited) return true;
    if (hi >= 11 && lo >= 11) return true; // JJ/TT already pairs handled; but KJ? etc
    if (suited && (hi - lo == 1) && hi >= 11) return true; // suited connectors JTs+
    return false;
}

static inline int clampInt(long long x, int lo, int hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return (int)x;
}

static int chooseRaise(int round, int a, int P, double p) {
    if (a <= 0) return 0;

    const double th[5] = {0.0, 0.58, 0.56, 0.55, 0.54};
    if (p < th[round]) return 0;

    long long x = 0;
    if (round == 1) {
        if (p > 0.80) x = 2LL * P;
        else if (p > 0.70) x = 1LL * P;
        else if (p > 0.63) x = 1LL * P / 2;
        else x = max(1LL, 1LL * P / 4);
    } else if (round == 2) {
        if (p > 0.86) x = a;
        else if (p > 0.76) x = 2LL * P;
        else if (p > 0.66) x = 1LL * P;
        else x = max(1LL, 1LL * P / 2);
    } else if (round == 3) {
        if (p > 0.88) x = a;
        else if (p > 0.78) x = 3LL * P;
        else if (p > 0.68) x = 2LL * P;
        else x = max(1LL, 1LL * P);
    } else { // round 4
        if (p > 0.90) x = a;
        else if (p > 0.82) x = a;
        else if (p > 0.72) x = 2LL * P;
        else x = max(1LL, 1LL * P);
    }

    x = clampInt(x, 1, a);
    return (int)x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // init deck
    int idx = 0;
    for (int s = 0; s < 4; s++) {
        for (int vl = 1; vl <= 13; vl++) {
            DECK[idx++] = Card{(uint8_t)s, (uint8_t)(vl + 1)}; // rank 2..14
        }
    }

    // init 7 choose 5 combos
    int ci = 0;
    for (int a = 0; a < 7; a++)
        for (int b = a + 1; b < 7; b++)
            for (int c = b + 1; c < 7; c++)
                for (int d = c + 1; d < 7; d++)
                    for (int e = d + 1; e < 7; e++)
                        COMBOS[ci++] = {a, b, c, d, e};

    int G;
    if (!(cin >> G)) return 0;

    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    string tok;
    while (cin >> tok) {
        if (tok == "-1") return 0;

        if (tok == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            cin >> tok; // ALICE
            if (tok == "-1") return 0;
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;

            Card hole[2] = {
                Card{(uint8_t)s1, (uint8_t)(v1 + 1)},
                Card{(uint8_t)s2, (uint8_t)(v2 + 1)}
            };

            cin >> tok; // BOARD
            if (tok == "-1") return 0;
            vector<Card> board;
            board.reserve(k);
            for (int i = 0; i < k; i++) {
                int s, v;
                cin >> s >> v;
                board.push_back(Card{(uint8_t)s, (uint8_t)(v + 1)});
            }

            int raiseAmt = 0;
            if (a > 0) {
                bool doSim = true;
                if (k == 0) doSim = preflopCandidate(hole[0], hole[1]);

                if (doSim) {
                    int samples;
                    if (k == 0) samples = 120;
                    else if (k == 3) samples = 140;
                    else if (k == 4) samples = 180;
                    else samples = 220;

                    Equity eq = estimateEquity(hole, board, samples, rng);
                    double p = eq.win + 0.5 * eq.tie;

                    raiseAmt = chooseRaise(r, a, P, p);
                }
            }

            if (raiseAmt <= 0) {
                cout << "ACTION CHECK\n" << flush;
            } else {
                cout << "ACTION RAISE " << raiseAmt << "\n" << flush;
            }
        } else if (tok == "OPP") {
            string what;
            cin >> what;
            if (what == "-1") return 0;
            if (what == "CALL") {
                long long x;
                cin >> x;
            }
        } else if (tok == "RESULT") {
            long long delta;
            cin >> delta;
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            return 0;
        } else if (tok == "RATES") {
            double w, d;
            cin >> w >> d;
        } else if (tok == "ALICE") {
            // Should not happen outside STATE; consume defensively
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
        } else if (tok == "BOARD") {
            // Defensive: no info about k here, ignore line-like tokens by not reading further.
        } else {
            // Unknown token: ignore (robustness)
        }
    }

    return 0;
}