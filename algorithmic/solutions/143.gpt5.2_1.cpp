#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    double nextDouble01() { // [0,1)
        uint64_t r = nextU64();
        return (r >> 11) * (1.0 / 9007199254740992.0); // 2^53
    }
};

static inline double clamp01(double v) {
    if (v < 0.0) return 0.0;
    if (v > 1.0) return 1.0;
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;

    const long long BUDGET_TOTAL = 3000000;
    long long usedBudget = 0;

    struct HandMem {
        double tightness = 0.0;
        bool pendingRaise = false;
        int lastPot = 0;
        int lastRaise = 0;
        int lastRound = 0;
        int handIdx = 0;
        XorShift64 rng;
        void reset(int h, uint64_t seed) {
            tightness = 0.0;
            pendingRaise = false;
            lastPot = 0;
            lastRaise = 0;
            lastRound = 0;
            handIdx = h;
            rng = XorShift64(seed);
        }
    } mem;

    auto dieIfMinusOne = [&](const string& tok) {
        if (tok == "-1") exit(0);
    };

    string tok;
    while (cin >> tok) {
        dieIfMinusOne(tok);

        if (tok == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            cin >> tok; dieIfMinusOne(tok); // ALICE
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;

            cin >> tok; dieIfMinusOne(tok); // BOARD
            vector<pair<int,int>> board;
            board.reserve(k);
            for (int i = 0; i < k; i++) {
                int s, v;
                cin >> s >> v;
                board.push_back({s, v});
            }

            if (h != mem.handIdx) {
                int id1 = s1 * 13 + (v1 - 1);
                int id2 = s2 * 13 + (v2 - 1);
                uint64_t seed = 0x9e3779b97f4a7c15ull;
                seed ^= (uint64_t)h * 0xbf58476d1ce4e5b9ull;
                seed ^= (uint64_t)(id1 + 1) * 0x94d049bb133111ebull;
                seed ^= (uint64_t)(id2 + 7) * 0x369dea0f31a53f85ull;
                seed ^= (uint64_t)(k + 11) * 0x2545f4914f6cdd1dull;
                mem.reset(h, seed);
            }

            long long remainingBudget = BUDGET_TOTAL - usedBudget;
            int remainingHands = max(1, G - h + 1);

            int baseT[5] = {0, 30, 50, 70, 100};
            int t = baseT[r];

            // Scale down if budget is tight
            long long avgPerHand = remainingBudget / remainingHands;
            if (avgPerHand < 210) {
                double scale = max(0.35, (double)avgPerHand / 210.0);
                t = max(15, (int)llround(t * scale));
            }
            if (remainingBudget <= 0) t = 0;
            else if (t > remainingBudget) t = (int)remainingBudget;
            if (t <= 0) t = 0;

            double w = 0.5, d = 0.0;
            if (t > 0) {
                cout << "RATE " << t << endl;
                usedBudget += t;

                string rt;
                cin >> rt;
                dieIfMinusOne(rt);
                if (rt != "RATES") exit(0);
                cin >> w >> d;
            }

            double p = clamp01(w + 0.5 * d);
            double pAdj = clamp01(p - mem.tightness);

            // Decision parameters
            double thr[5] = {0.0, 0.55, 0.53, 0.525, 0.52};

            double baseMult[5] = {0.0, 0.45, 0.55, 0.65, 0.80};
            double coefMult[5] = {0.0, 4.0, 5.0, 6.0, 8.0};

            double maxFrac[5] = {0.0, 0.35, 0.45, 0.65, 1.0};

            bool doRaise = false;
            long long raiseX = 0;

            // Occasional river bluffing when no strong signal from calls
            bool canBluff = (r == 4 && mem.tightness < 0.04 && P >= 25 && a >= 6);
            if (pAdj < thr[r]) {
                if (canBluff) {
                    double bluffProb = 0.0;
                    if (pAdj < 0.22) bluffProb = 0.18;
                    else if (pAdj < 0.30) bluffProb = 0.12;
                    else if (pAdj < 0.40) bluffProb = 0.06;
                    else bluffProb = 0.0;

                    // Slightly higher bluffing when pot is big relative to stack
                    if (P >= 60) bluffProb *= 1.2;
                    bluffProb = min(0.22, bluffProb);

                    if (mem.rng.nextDouble01() < bluffProb) {
                        long long bx = (long long)llround(P * 1.05);
                        bx = max(1LL, bx);
                        bx = min<long long>(bx, a);
                        // Respect earlier street caps? On river allow full.
                        if (bx >= 1) {
                            doRaise = true;
                            raiseX = bx;
                        }
                    }
                }
            } else {
                double edge = max(0.0, pAdj - 0.5);
                double mult = baseMult[r] + coefMult[r] * edge;

                // Mild dampening when pAdj is just barely above threshold
                if (pAdj < thr[r] + 0.02) mult *= 0.85;

                long long bx = (long long)llround((double)P * mult);
                bx = max(1LL, bx);

                long long capByFrac = (long long)floor((double)a * maxFrac[r] + 1e-9);
                capByFrac = max(1LL, capByFrac);
                bx = min(bx, capByFrac);
                bx = min<long long>(bx, a);

                // Ensure some minimum to build pot with very strong hands
                if (r <= 2 && P <= 14 && pAdj >= 0.72) bx = max(bx, 8LL);
                if (r == 1 && pAdj >= 0.80) bx = max(bx, 14LL);

                bx = min<long long>(bx, a);

                if (bx >= 1) {
                    doRaise = true;
                    raiseX = bx;
                }
            }

            if (!doRaise || a <= 0) {
                cout << "ACTION CHECK" << endl;
                mem.pendingRaise = false;
            } else {
                raiseX = max(1LL, min<long long>(raiseX, a));
                cout << "ACTION RAISE " << raiseX << endl;
                mem.pendingRaise = true;
                mem.lastPot = P;
                mem.lastRaise = (int)raiseX;
                mem.lastRound = r;
            }
        } else if (tok == "OPP") {
            string act;
            cin >> act;
            dieIfMinusOne(act);
            if (act == "CALL") {
                int x;
                cin >> x;
                if (mem.pendingRaise) {
                    double ratio = (double)x / (double)max(1, mem.lastPot);
                    double add = min(0.06, 0.02 + 0.01 * ratio);
                    mem.tightness = min(0.12, mem.tightness + add);
                }
                mem.pendingRaise = false;
            } else if (act == "FOLD") {
                mem.pendingRaise = false;
            } else if (act == "CHECK") {
                mem.pendingRaise = false;
            } else {
                mem.pendingRaise = false;
            }
        } else if (tok == "RESULT") {
            int delta;
            cin >> delta;
            mem.reset(0, mem.rng.nextU64());
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            break;
        } else {
            // Unknown token; if judge is well-formed this shouldn't happen.
            // Consume line defensively.
        }
    }

    return 0;
}