#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    string cmd;
    while (cin >> cmd) {
        if (cmd == "-1") return 0;

        if (cmd == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string alice;
            cin >> alice; // "ALICE"
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;

            string board;
            cin >> board; // "BOARD"
            for (int i = 0; i < 2 * k; ++i) {
                int tmp;
                cin >> tmp;
            }

            // Simple strategy: always check.
            cout << "ACTION CHECK" << endl;

        } else if (cmd == "OPP") {
            string what;
            cin >> what;
            if (what == "CALL") {
                int x;
                cin >> x;
            } else if (what == "FOLD") {
                // nothing more on this line
            } else if (what == "CHECK") {
                // nothing more on this line
            }
        } else if (cmd == "RESULT") {
            int delta;
            cin >> delta; // may be negative; ignore
        } else if (cmd == "RATES") {
            double w, d;
            cin >> w >> d; // ignore
        } else if (cmd == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (cmd == "ALICE") {
            // Should normally be handled inside STATE, but guard just in case
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
        } else if (cmd == "BOARD") {
            // Should normally be handled inside STATE
            // k is unknown here, but this path should not occur in normal protocol
            // Consume rest of line defensively
            string line;
            getline(cin, line);
        } else {
            // Unknown token; consume rest of line defensively
            string line;
            getline(cin, line);
        }
    }

    return 0;
}