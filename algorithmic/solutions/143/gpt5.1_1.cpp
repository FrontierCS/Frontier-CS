#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string first;
    if (!(cin >> first)) return 0;
    if (first == "-1") return 0;
    int G = stoi(first);
    (void)G; // unused

    string cmd;
    while (cin >> cmd) {
        if (cmd == "-1") return 0;

        if (cmd == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string label;
            cin >> label;                 // "ALICE"
            if (label == "-1") return 0;
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;  // hole cards

            string boardLabel;
            cin >> boardLabel;            // "BOARD"
            if (boardLabel == "-1") return 0;
            for (int i = 0; i < k; ++i) {
                int cs, cv;
                cin >> cs >> cv;          // community cards
            }

            // Simple strategy: always check.
            cout << "ACTION CHECK" << endl;
            cout.flush();
        } else if (cmd == "OPP") {
            string action;
            cin >> action;
            if (action == "-1") return 0;
            if (action == "CALL") {
                int x;
                cin >> x; // amount called
            } else if (action == "FOLD") {
                // nothing extra
            } else if (action == "CHECK") {
                // nothing
            }
        } else if (cmd == "RESULT") {
            int delta;
            cin >> delta; // may be negative, including -1; do NOT treat as termination
        } else if (cmd == "SCORE") {
            double W;
            cin >> W;
            // match over
            break;
        } else if (cmd == "RATES") {
            double w, d;
            cin >> w >> d; // we never request RATE, but handle just in case
        } else if (cmd == "ALICE") {
            // Should only appear immediately after STATE; but handle defensively
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;
        } else if (cmd == "BOARD") {
            // Defensive: read unknown number of cards? Spec says k in STATE; here we don't know k.
            // We'll just read to end of line and ignore.
            string rest;
            getline(cin, rest);
        } else {
            // Unknown token; consume rest of line
            string rest;
            getline(cin, rest);
        }
    }

    return 0;
}