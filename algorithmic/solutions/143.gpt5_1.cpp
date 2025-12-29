#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t s;
    RNG() { s = 88172645463393265ull; }
    uint64_t next() { s ^= s << 7; s ^= s >> 9; return s; }
    double drand() { return (next() >> 11) * (1.0/9007199254740992.0); }
} rng;

static const long long RATE_BUDGET_LIMIT = 3000000;
static long long rate_used = 0;

bool readToken(string &tok) {
    if (!(cin >> tok)) return false;
    if (tok == "-1") exit(0);
    return true;
}

pair<double,double> requestRate(int t) {
    cout << "RATE " << t << endl;
    cout.flush();
    string tok;
    if (!readToken(tok)) return {0.0,0.0};
    if (tok == "RATES") {
        double w, d;
        cin >> w >> d;
        return {w, d};
    }
    if (tok == "-1") exit(0);
    // In case of unexpected tokens, attempt to sync (shouldn't happen).
    return {0.0, 0.0};
}

int chooseRaiseAmount(int r, int a, int P, double E, int t) {
    if (a <= 0) return 0;
    // Estimate sampling uncertainty conservatively
    double se = 0.5 / sqrt(max(1, t));
    double confK = 1.5; // 1.5-sigma lower bound
    double Elower = E - confK * se;

    if (Elower <= 0.5) return 0; // only value bet when we're confidently ahead

    // Strong thresholds for all-in by round using lower-bound equity
    double thrAI;
    if (r == 1) thrAI = 0.60;
    else if (r == 2) thrAI = 0.58;
    else if (r == 3) thrAI = 0.56;
    else thrAI = 0.54;

    if (Elower >= thrAI) return a; // shove

    // Otherwise, make a moderate value raise based on pot and round
    int x = 0;
    if (r == 1) {
        // Preflop: small to medium raise
        x = (int)floor(0.8 * P + 8);
    } else if (r == 2) {
        x = (int)floor(1.0 * P + 8);
    } else if (r == 3) {
        x = (int)floor(1.2 * P + 8);
    } else {
        // River: larger value raise
        x = (int)floor(1.5 * P + 10);
    }
    x = max(1, min(a, x));
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    if (!readToken(tok)) return 0;
    // First token is G (number of hands)
    int G = 0;
    {
        // tok should be integer G
        G = stoi(tok);
    }

    // RATE t per round to respect budget (~300 per hand)
    auto rateT = [&](int r)->int {
        if (r == 1) return 20;
        if (r == 2) return 40;
        if (r == 3) return 60;
        return 180; // r == 4
    };

    while (true) {
        if (!readToken(tok)) break;
        if (tok == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;
            string al; cin >> al; // "ALICE"
            int c1, v1, c2, v2;
            cin >> c1 >> v1 >> c2 >> v2;
            string bd; cin >> bd; // "BOARD"
            for (int i = 0; i < 2 * k; ++i) { int tmp; cin >> tmp; (void)tmp; }

            int t = rateT(r);
            double w = 0.0, d = 0.0;
            if (a > 0 && rate_used + t <= RATE_BUDGET_LIMIT) {
                auto res = requestRate(t);
                w = res.first; d = res.second;
                rate_used += t;
            } else {
                // If no budget or no chips, avoid RATE and just check
                // unless trivially strong situations: we don't compute strength; default to check.
            }
            double E = w + 0.5 * d;

            int x = 0;
            if (a > 0 && (rate_used > 0)) {
                x = chooseRaiseAmount(r, a, P, E, max(1, (r==1?20:r==2?40:r==3?60:180)));
            } else {
                x = 0;
            }

            if (x <= 0) {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            } else {
                cout << "ACTION RAISE " << x << endl;
                cout.flush();
            }
        } else if (tok == "ALICE") {
            // Should only appear after STATE; consume line safely if encountered unexpectedly
            int c1, v1, c2, v2;
            cin >> c1 >> v1 >> c2 >> v2;
        } else if (tok == "BOARD") {
            // Consume remaining ints on this BOARD line if any (unknown k); since protocol sends explicit k in STATE,
            // "BOARD" alone here is unexpected; consume until end of line (not trivial with >>).
            // We'll skip: assume "BOARD" here only occurs immediately after STATE and we've already handled it.
        } else if (tok == "RATES") {
            // Normally handled inside requestRate; but in case it appears here, consume
            double w, d;
            cin >> w >> d;
        } else if (tok == "OPP") {
            string what; cin >> what;
            if (what == "CHECK") {
                // nothing
            } else if (what == "FOLD") {
                // nothing; RESULT should come next
            } else if (what == "CALL") {
                int x; cin >> x; (void)x;
            }
        } else if (tok == "RESULT") {
            int delta; cin >> delta; (void)delta;
        } else if (tok == "SCORE") {
            double W; cin >> W; (void)W;
            // End of match likely
            break;
        } else {
            // Unknown token; ignore
        }
    }
    return 0;
}