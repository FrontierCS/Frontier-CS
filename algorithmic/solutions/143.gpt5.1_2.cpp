#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    const int RATE_PER_RIVER = 200;
    const double EPS = 0.05; // safety margin over 2w + d > 1

    string token;
    while (cin >> token) {
        if (token == "-1") return 0;

        if (token == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string label;
            cin >> label; // "ALICE"
            if (label == "-1") return 0;

            int c1s, c1v, c2s, c2v;
            cin >> c1s >> c1v >> c2s >> c2v;

            cin >> label; // "BOARD"
            if (label == "-1") return 0;

            for (int i = 0; i < k; ++i) {
                int s, v;
                cin >> s >> v;
            }

            double w = 0.0, d = 0.0;
            if (r == 4) {
                cout << "RATE " << RATE_PER_RIVER << endl;

                string tag;
                if (!(cin >> tag)) return 0;
                if (tag == "-1") return 0;
                if (tag != "RATES") return 0;
                cin >> w >> d;
            }

            if (r < 4) {
                cout << "ACTION CHECK" << endl;
            } else {
                double s = 2.0 * w + d;
                if (s > 1.0 + EPS && a > 0) {
                    int x = min(20, a);
                    if (x < 1) x = 1;
                    cout << "ACTION RAISE " << x << endl;
                } else {
                    cout << "ACTION CHECK" << endl;
                }
            }
        } else if (token == "OPP") {
            string act;
            cin >> act;
            if (act == "-1") return 0;
            if (act == "CALL") {
                int x;
                cin >> x;
            } else if (act == "FOLD") {
                // nothing
            } else if (act == "CHECK") {
                // nothing
            }
        } else if (token == "RESULT") {
            int delta;
            cin >> delta;
        } else if (token == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (token == "RATES") {
            // Should not happen at top level; consume to stay in sync.
            double w_ignore, d_ignore;
            cin >> w_ignore >> d_ignore;
        } else {
            // Unknown or unexpected token; exit to avoid protocol violation.
            return 0;
        }
    }

    return 0;
}