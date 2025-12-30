#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Global budget tracking
long long used_budget = 0;
const long long MAX_BUDGET = 3000000;

void solve() {
    string token;
    while (cin >> token) {
        if (token == "SCORE") {
            // Match ended, read score and exit loop
            double w; 
            if (cin >> w) {};
            break;
        }
        if (token == "-1") {
            // Error or forced termination
            exit(0);
        }

        if (token == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string dummy;
            cin >> dummy; // "ALICE"
            int c1s, c1v, c2s, c2v;
            cin >> c1s >> c1v >> c2s >> c2v;

            cin >> dummy; // "BOARD"
            vector<pair<int, int>> board(k);
            for (int i = 0; i < k; ++i) {
                cin >> board[i].first >> board[i].second;
            }

            // Determine RATE samples to use based on the round/street
            // We allocate more budget to later streets where pots are larger
            // Total budget 3M for 10k hands = 300/hand avg.
            int samples = 0;
            if (k == 0) samples = 40;       // Preflop
            else if (k == 3) samples = 60;  // Flop
            else if (k == 4) samples = 80;  // Turn
            else samples = 100;             // River (k=5)

            // Budget check
            if (used_budget + samples > MAX_BUDGET) {
                samples = (int)(MAX_BUDGET - used_budget);
                if (samples < 0) samples = 0;
            }

            double equity = 0.5; // Default neutral equity

            if (samples > 0) {
                cout << "RATE " << samples << endl;
                string rtoken;
                cin >> rtoken; // Should be "RATES" or "-1"
                if (rtoken == "-1") exit(0);
                
                double w, d;
                cin >> w >> d;
                equity = w + d * 0.5;
                used_budget += samples;
            } else {
                // Out of budget fallback heuristic
                // Cards are 1..13 (2..A). 10=J, 11=Q, 12=K, 13=A
                bool pair = (c1v == c2v);
                bool high = (c1v >= 10 || c2v >= 10);
                if (pair || high) equity = 0.6;
                else equity = 0.4;
            }

            // Decision Logic
            // The opponent is passive (checks back).
            // We check with marginal hands to realize equity for free.
            // We raise for value when we have an advantage.
            
            double raise_thresh = 0.60;
            double monster_thresh = 0.85;
            
            string action = "CHECK";
            int raise_amt = 0;

            // Only raise if we have a stack to bet and good equity
            if (equity > raise_thresh && a > 0) {
                double sizing = 0.5; // Half pot
                if (equity > monster_thresh) sizing = 1.0; // Pot size

                int x = (int)(P * sizing);
                // Ensure raise is valid [1, a]
                if (x < 1) x = 1;
                if (x > a) x = a;
                
                action = "RAISE";
                raise_amt = x;
            }

            if (action == "RAISE") {
                cout << "ACTION RAISE " << raise_amt << endl;
            } else {
                cout << "ACTION CHECK" << endl;
            }

        } else if (token == "OPP") {
            string sub; cin >> sub;
            if (sub == "CALL") {
                int x; cin >> x;
            }
            // If FOLD or CHECK, no additional data follows on this line.
            // The next token will be RESULT (if Fold) or STATE/RESULT (if Check).
        } else if (token == "RESULT") {
            int delta; cin >> delta;
            // Hand ended
        } else {
            // Should not happen in correct protocol execution
        }
    }
}

int main() {
    // Faster I/O, but ensure we flush every line with endl
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int G;
    if (cin >> G) {
        solve();
    }
    return 0;
}