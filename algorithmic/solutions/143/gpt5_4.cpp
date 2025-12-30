#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long MAX_BUDGET = 3000000;
    long long budgetRemaining = MAX_BUDGET;

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    // Base sampling per round (1..4). Keep conservative to stay under 3,000,000 total.
    int baseT[5] = {0, 30, 45, 60, 90}; // sum per hand worst-case: 225

    string token;
    while (cin >> token) {
        if (token == "-1") return 0;

        if (token == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;
            string aliceWord;
            cin >> aliceWord;
            if (aliceWord == "-1") return 0;
            int c1, v1, c2, v2;
            cin >> c1 >> v1 >> c2 >> v2;

            string boardWord;
            cin >> boardWord;
            if (boardWord == "-1") return 0;
            for (int i = 0; i < k; ++i) {
                int cs, vs;
                cin >> cs >> vs;
            }

            // Query RATE with limited budget
            double w = 0.0, d = 0.0;
            int t = 0;
            if (budgetRemaining > 0) {
                t = min<long long>(baseT[r], budgetRemaining);
                if (t > 0) {
                    cout << "RATE " << t << endl;
                    cout.flush();
                    string ratesWord;
                    if (!(cin >> ratesWord)) return 0;
                    if (ratesWord == "-1") return 0;
                    if (ratesWord != "RATES") {
                        // Protocol expects RATES here; if not, try to recover by scanning until RATES
                        // But per spec, it should be RATES directly.
                        // Fail-safe: return
                        return 0;
                    }
                    cin >> w >> d;
                    budgetRemaining -= t;
                }
            }

            double e = w + 0.5 * d; // our equity

            // Strategy: pure value betting.
            // If equity > 0.5 + margin, choose raise size to encourage a call:
            // choose maximum x such that x/(P + 2x) <= 1 - e - m  => calls likely.
            // Else, CHECK.
            double margin = 0.02;
            if (a > 0 && e > 0.5 + margin) {
                double denom = 2.0 * e + 2.0 * margin - 1.0;
                double alpha = 1.0 - e - margin;
                long long x = 1;
                if (denom > 1e-12 && alpha > -1e-12) {
                    double x_max_real = (alpha * (double)P) / denom;
                    long long x_max = (long long)floor(x_max_real + 1e-9);
                    if (x_max < 1) x_max = 1;
                    if (x_max > a) x_max = a;
                    x = x_max;
                } else {
                    // Extremely strong equity; raise minimum to get called often
                    x = 1;
                }
                if (x < 1) x = 1;
                if (x > a) x = a;
                cout << "ACTION RAISE " << x << endl;
                cout.flush();
            } else {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            }
        } else if (token == "RATES") {
            // Unexpected standalone RATES; consume and ignore to resync
            double w, d;
            cin >> w >> d;
            // ignore
        } else if (token == "OPP") {
            string resp;
            cin >> resp;
            if (resp == "CALL") {
                long long x;
                cin >> x;
            } else if (resp == "CHECK") {
                // nothing
            } else if (resp == "FOLD") {
                // nothing
            } else if (resp == "-1") {
                return 0;
            } else {
                // unexpected, ignore
            }
        } else if (token == "RESULT") {
            long long delta;
            cin >> delta;
        } else if (token == "SCORE") {
            double W;
            cin >> W;
            // match ended
            break;
        } else {
            // Unknown token, read/ignore
        }
    }

    return 0;
}