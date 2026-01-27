#include <bits/stdc++.h>
using namespace std;

static const double EPS = 1e-9;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    if (!(cin >> tok)) return 0;
    if (tok == "-1") return 0;
    // First token should be G (number of hands)
    // But could be directly an integer without label
    int G = 0;
    {
        // tok should be integer G
        G = stoi(tok);
    }

    auto queryRate = [&](int t, double &w, double &d) -> bool {
        cout << "RATE " << t << "\n";
        cout.flush();
        string tkn;
        while (cin >> tkn) {
            if (tkn == "-1") return false;
            if (tkn == "RATES") {
                cin >> w >> d;
                return true;
            }
            // consume rest tokens for other lines if any unexpected, but typically only RATES arrives here
        }
        return false;
    };

    // Main loop: process tokens, act on STATE
    while (cin >> tok) {
        if (tok == "-1") {
            return 0;
        } else if (tok == "STATE") {
            // Parse STATE h r a b P k
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            // Next line: ALICE c1 v1 c2 v2
            string aliceTok;
            cin >> aliceTok;
            if (aliceTok == "-1") return 0;
            // Should be "ALICE"
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;

            // Next line: BOARD [2k ints]
            string boardTok;
            cin >> boardTok;
            if (boardTok == "-1") return 0;
            // Should be "BOARD"
            for (int i = 0; i < 2 * k; ++i) {
                int tmp;
                cin >> tmp;
            }

            // Decide t based on k/round, aiming to keep under budget
            int t = 60;
            if (k == 0) t = 80;
            else if (k == 3) t = 70;
            else if (k == 4) t = 60;
            else if (k == 5) t = 50;

            double w = 0.0, d = 0.0;
            if (!queryRate(t, w, d)) return 0;

            // Strategy:
            // - Never FOLD.
            // - If 2w + d > 1 and a >= 1, RAISE x to induce fold or get +EV call.
            //   Choose x ~ ceil(x* + 1), where x* = P*(1 - w - d/2)/(2w + d - 1).
            //   Clamp x to [1, a].
            // - Else CHECK.
            double s = 2.0 * w + d;

            if (a >= 1 && s > 1.0 + 1e-3) {
                double denom = s - 1.0;
                double numer = P * (1.0 - w - 0.5 * d);
                double xstar = 0.0;
                if (denom > EPS) {
                    xstar = numer / denom;
                } else {
                    xstar = -1e18; // shouldn't happen due to s>1
                }
                long long x;
                if (xstar <= 0.0) {
                    x = 1; // any raise should fold in theory
                } else {
                    // Add a small safety margin
                    x = (long long)ceil(xstar + 1.0);
                }
                if (x < 1) x = 1;
                if (x > a) x = a;
                cout << "ACTION RAISE " << x << "\n";
                cout.flush();
            } else {
                cout << "ACTION CHECK\n";
                cout.flush();
            }
        } else if (tok == "OPP") {
            // Read opponent response: CHECK, FOLD, or CALL x
            string what;
            cin >> what;
            if (what == "-1") return 0;
            if (what == "CALL") {
                long long x;
                cin >> x;
            }
            // else CHECK or FOLD: nothing more on this line
        } else if (tok == "RESULT") {
            long long delta;
            cin >> delta;
            // Hand ended; continue
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            // Match ended; break
            break;
        } else if (tok == "RATES") {
            // Shouldn't happen here except if out-of-order; consume and continue
            double w, d;
            cin >> w >> d;
        } else if (tok == "ALICE") {
            // Out-of-order safety: consume four ints
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
        } else if (tok == "BOARD") {
            // Without knowing k here, can't read accurately; but this shouldn't occur without STATE
            // As a fallback, read rest of line
            string line;
            getline(cin, line);
        } else {
            // Unknown token: consume rest of line
            string line;
            getline(cin, line);
        }
    }
    return 0;
}