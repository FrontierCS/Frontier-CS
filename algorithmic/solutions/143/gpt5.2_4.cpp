#include <bits/stdc++.h>
using namespace std;

struct Card {
    int s, v;
};

static std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const long long BUDGET = 3000000;
    long long used = 0;

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    string pending;

    auto nextTok = [&]() -> string {
        if (!pending.empty()) {
            string t = pending;
            pending.clear();
            return t;
        }
        string t;
        if (!(cin >> t)) return "";
        return t;
    };

    auto computeT = [&](int h, int r, int a, int P) -> int {
        if (a <= 0) return 0;

        int base[5] = {0, 35, 60, 80, 110};
        int t = base[r];

        if (r >= 3 && P >= 90) t += 25;
        if (r == 4 && P >= 140) t += 35;

        long long rem = BUDGET - used;
        if (rem <= 0) return 0;
        if (t > rem) t = (int)rem;
        if (t < 1) t = 0;
        return t;
    };

    auto chooseRaise = [&](int r, int a, int P, double e, int t) -> int {
        if (a <= 0) return 0;

        double streetMul[5] = {0.0, 0.90, 1.00, 1.10, 1.25};
        double mul = streetMul[r];

        double margin = 0.012;
        if (t > 0) margin += 0.10 / sqrt((double)t);
        double eCons = e - margin;

        auto clampA = [&](long long x) -> int {
            if (x < 1) return 1;
            if (x > a) return a;
            return (int)x;
        };

        int x = 0;
        if (eCons >= 0.505) {
            double f = 0.0;
            if (eCons < 0.54) f = 0.35;
            else if (eCons < 0.58) f = 0.70;
            else if (eCons < 0.63) f = 1.20;
            else if (eCons < 0.68) f = 1.80;
            else if (eCons < 0.74) f = 2.60;
            else if (eCons < 0.80) f = 3.80;
            else if (eCons < 0.86) f = 5.50;
            else return a;

            long long raw = llround((double)P * f * mul);
            x = clampA(raw);

            // Soft caps on earlier streets to reduce over-commitment with medium edges.
            if (r == 1) x = min(x, min(a, 55));
            if (r == 2) x = min(x, min(a, 80));
            if (r == 3) x = min(x, min(a, 95));
        }

        // River bluff sometimes when weak.
        if (r == 4 && x == 0 && P >= 25) {
            double pBluff = 0.0;
            if (eCons < 0.20) pBluff = 0.26;
            else if (eCons < 0.28) pBluff = 0.18;
            else if (eCons < 0.36) pBluff = 0.10;
            else if (eCons < 0.42) pBluff = 0.06;

            uniform_real_distribution<double> U(0.0, 1.0);
            if (U(rng) < pBluff) {
                int bx = (int)llround((double)P * 1.5);
                bx = min(bx, 2 * P);
                bx = clampA(bx);
                x = bx;
            }
        }

        return x;
    };

    while (true) {
        string tok = nextTok();
        if (tok.empty()) break;
        if (tok == "-1") break;

        if (tok == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string s = nextTok();
            if (s == "-1") break;
            if (s != "ALICE") return 0;

            Card hole[2];
            cin >> hole[0].s >> hole[0].v >> hole[1].s >> hole[1].v;

            string sb = nextTok();
            if (sb == "-1") break;
            if (sb != "BOARD") return 0;

            vector<Card> board;
            board.reserve(k);
            for (int i = 0; i < k; i++) {
                Card c;
                cin >> c.s >> c.v;
                board.push_back(c);
            }

            int t = computeT(h, r, a, P);
            double w = 0.0, d = 0.0, e = 0.5;

            if (t > 0) {
                cout << "RATE " << t << endl;
                cout.flush();
                used += t;

                string rt = nextTok();
                if (rt == "-1" || rt.empty()) break;
                if (rt != "RATES") return 0;
                cin >> w >> d;
                e = w + 0.5 * d;
            }

            int x = chooseRaise(r, a, P, e, t);

            if (x <= 0 || a <= 0) {
                cout << "ACTION CHECK" << endl;
            } else {
                cout << "ACTION RAISE " << x << endl;
            }
            cout.flush();

            string opp = nextTok();
            if (opp == "-1" || opp.empty()) break;
            if (opp != "OPP") return 0;

            string oact;
            cin >> oact;
            if (oact == "CALL") {
                long long cx;
                cin >> cx;
            } else if (oact == "FOLD") {
                // nothing
            } else if (oact == "CHECK") {
                // nothing
            } else {
                return 0;
            }

            string nt = nextTok();
            if (nt == "-1" || nt.empty()) break;

            if (nt == "RESULT") {
                int delta;
                cin >> delta;
                // Next token will be either STATE for next hand or SCORE at end.
            } else if (nt == "STATE" || nt == "SCORE") {
                pending = nt;
            } else {
                // Unexpected, but keep going with pending to avoid desync.
                pending = nt;
            }
        } else if (tok == "RESULT") {
            int delta;
            cin >> delta;
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (tok == "RATES") {
            // Should not happen unless we desynced; consume.
            double w, d;
            cin >> w >> d;
        } else {
            // Unknown token; try to continue or exit.
            return 0;
        }
    }

    return 0;
}