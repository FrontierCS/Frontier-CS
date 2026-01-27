#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const long long BUDGET_TOTAL = 3000000;
    long long spent = 0;

    string line;
    if (!getline(cin, line)) return 0;
    {
        if (line == "-1") return 0;
        // First line should be G
        // But sometimes there can be extra spaces; parse robustly
        stringstream ss(line);
        long long G;
        if (!(ss >> G)) return 0;
        if (G == -1) return 0;
    }

    auto getRates = [&](int t, double &w, double &d) -> bool {
        if (t <= 0) { w = 0.5; d = 0.0; return true; }
        cout << "RATE " << t << endl;
        cout.flush();
        string rline;
        while (true) {
            if (!getline(cin, rline)) return false;
            if (rline == "-1") return false;
            if (rline.empty()) continue;
            string tok;
            stringstream rs(rline);
            rs >> tok;
            if (tok == "RATES") {
                if (!(rs >> w >> d)) { w = 0.5; d = 0.0; }
                return true;
            }
            // In case of unexpected lines before RATES, continue reading
        }
    };

    // Main loop: read lines and react on STATE
    while (getline(cin, line)) {
        if (line == "-1") return 0;
        if (line.empty()) continue;
        stringstream ss(line);
        string tok;
        ss >> tok;
        if (tok == "STATE") {
            int h, r, a, b, P, k;
            ss >> h >> r >> a >> b >> P >> k;
            // Read ALICE line
            string aliceLine;
            if (!getline(cin, aliceLine)) return 0;
            if (aliceLine == "-1") return 0;
            // Read BOARD line
            string boardLine;
            if (!getline(cin, boardLine)) return 0;
            if (boardLine == "-1") return 0;

            // Decide whether to query rates
            int t = 0;
            if (r == 1) t = 60;
            else if (r == 2) t = 120;
            else if (r == 3) t = 120;
            else t = 0;

            if (spent + t > BUDGET_TOTAL) {
                t = max(0LL, BUDGET_TOTAL - spent);
            }
            double w = 0.5, d = 0.0;
            if (t > 0) {
                if (!getRates(t, w, d)) return 0;
                spent += t;
            } else {
                w = 0.5; d = 0.0;
            }
            double p = w + 0.5 * d;

            // Thresholds per round
            double thr = 0.0;
            if (r == 1) thr = 0.54;
            else if (r == 2) thr = 0.57;
            else if (r == 3) thr = 0.60;

            // Choose action
            if (r == 4) {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            } else {
                bool doRaise = (p >= thr) && (a >= 1);
                int x = 1;
                if (doRaise) {
                    if (r == 1) {
                        x = max(1, P / 3);
                        x = min(x, 5);
                    } else if (r == 2) {
                        x = max(2, P / 2);
                        x = min(x, 10);
                    } else { // r == 3
                        x = max(2, P / 2);
                        x = min(x, 15);
                    }
                    x = max(1, min(x, a));
                }
                if (doRaise && x >= 1) {
                    cout << "ACTION RAISE " << x << endl;
                    cout.flush();
                } else {
                    cout << "ACTION CHECK" << endl;
                    cout.flush();
                }
            }
        } else {
            // Other lines: OPP CHECK/FOLD/CALL, RESULT, SCORE, etc. Just continue.
            // If RESULT or SCORE appears, nothing special to do.
            continue;
        }
    }
    return 0;
}