#include <bits/stdc++.h>
using namespace std;

string readToken() {
    string t;
    if (!(cin >> t)) {
        exit(0);
    }
    if (t == "-1") {
        exit(0);
    }
    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read number of hands G (unused, but required by protocol)
    string gTok = readToken();
    int G = stoi(gTok);
    (void)G;

    while (true) {
        string tok = readToken();

        if (tok == "STATE") {
            // STATE h r a b P k
            int h = stoi(readToken());
            int r = stoi(readToken());
            int a = stoi(readToken());
            int b = stoi(readToken());
            int P = stoi(readToken());
            int k = stoi(readToken());
            (void)h; (void)r; (void)a; (void)b; (void)P;

            // ALICE c1 v1 c2 v2
            string aliceTok = readToken(); // "ALICE"
            (void)aliceTok;
            int c1 = stoi(readToken());
            int v1 = stoi(readToken());
            int c2 = stoi(readToken());
            int v2 = stoi(readToken());
            (void)c1; (void)v1; (void)c2; (void)v2;

            // BOARD [2k ints]
            string boardTok = readToken(); // "BOARD"
            (void)boardTok;
            for (int i = 0; i < 2 * k; ++i) {
                int x = stoi(readToken());
                (void)x;
            }

            // Simple strategy: always CHECK
            cout << "ACTION CHECK" << endl;
        } else if (tok == "OPP") {
            string act = readToken(); // CHECK, FOLD, or CALL
            if (act == "CALL") {
                string sx = readToken(); // amount
                (void)sx;
            }
            // For CHECK or FOLD, nothing more to read on this line
        } else if (tok == "RESULT") {
            string deltaTok = readToken(); // integer profit
            (void)deltaTok;
        } else if (tok == "SCORE") {
            string wTok = readToken(); // final average profit (double)
            (void)wTok;
            break;
        } else if (tok == "RATES") {
            // We never send RATE, so this should not occur, but handle defensively.
            string w = readToken();
            string d = readToken();
            (void)w; (void)d;
        } else if (tok == "ALICE") {
            // Should only appear immediately after STATE, but handle defensively.
            for (int i = 0; i < 4; ++i) {
                readToken();
            }
        } else if (tok == "BOARD") {
            // Without knowing k, we can't safely consume; this should not happen standalone.
            // Do nothing; protocol guarantees BOARD appears only where expected.
        } else if (tok == "RATE") {
            // We never send RATE, but if encountered, consume its parameter.
            readToken();
        } else {
            // Unknown token; protocol should not send this. Ignore.
        }
    }

    return 0;
}