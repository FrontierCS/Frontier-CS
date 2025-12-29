#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;

    const int TOTAL_BUDGET = 3000000;
    int remainingBudget = TOTAL_BUDGET;

    string token;
    while (cin >> token) {
        if (token == "-1") {
            return 0;
        } else if (token == "STATE") {
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            string sAlice;
            cin >> sAlice;
            if (sAlice == "-1") return 0;
            int cs1, v1, cs2, v2;
            if (sAlice == "ALICE") {
                cin >> cs1 >> v1 >> cs2 >> v2;
            } else {
                // Unexpected, but try to recover
                // Consume four integers anyway
                cin >> cs1 >> v1 >> cs2 >> v2;
            }

            string sBoard;
            cin >> sBoard;
            if (sBoard == "-1") return 0;
            vector<pair<int,int>> board;
            if (sBoard == "BOARD") {
                for (int i = 0; i < k; ++i) {
                    int cs, vs;
                    cin >> cs >> vs;
                    board.push_back({cs, vs});
                }
            } else {
                // Unexpected token, skip line
                string rest;
                getline(cin, rest);
            }

            double winProb = 0.0, tieProb = 0.0;
            bool willQueryRate = false;
            int tSamples = 0;

            if (r == 4 && k == 5 && a > 0 && remainingBudget > 0) {
                int handsLeft = G - h + 1;
                if (handsLeft < 1) handsLeft = 1;
                int reservedPerHand = remainingBudget / handsLeft;
                if (reservedPerHand < 100) reservedPerHand = 100;
                tSamples = min(500, reservedPerHand);
                if (tSamples > remainingBudget) tSamples = remainingBudget;
                if (tSamples < 10 && remainingBudget >= 10) tSamples = 10;
                if (tSamples > 0) {
                    willQueryRate = true;
                    remainingBudget -= tSamples;
                    cout << "RATE " << tSamples << "\n" << flush;
                    string resToken;
                    if (!(cin >> resToken)) return 0;
                    if (resToken == "-1") return 0;
                    if (resToken == "RATES") {
                        cin >> winProb >> tieProb;
                    } else {
                        // Unexpected, try to recover minimally
                        double tmp1, tmp2;
                        cin >> tmp1 >> tmp2;
                    }
                }
            }

            if (r == 4 && k == 5 && a > 0 && willQueryRate) {
                double W = winProb;
                double D = tieProb;
                double metric = 2.0 * W + D;
                // Conservative threshold for value-raising
                const double THRESHOLD = 1.4;
                if (metric > THRESHOLD) {
                    int x = a; // all-in
                    cout << "ACTION RAISE " << x << "\n" << flush;
                } else {
                    cout << "ACTION CHECK\n" << flush;
                }
            } else {
                cout << "ACTION CHECK\n" << flush;
            }
        } else if (token == "RATES") {
            double w, d;
            cin >> w >> d;
            // These should only appear as responses to our RATE,
            // which we already consumed in the STATE block.
            // Ignore here.
        } else if (token == "OPP") {
            string what;
            cin >> what;
            if (what == "-1") return 0;
            if (what == "CALL") {
                int x;
                cin >> x;
            } else if (what == "FOLD") {
                // Nothing extra
            } else if (what == "CHECK") {
                // Nothing extra
            } else {
                // Unexpected, try to consume possible integer
                int x;
                if (cin >> x) { /* ignore */ }
            }
        } else if (token == "RESULT") {
            int delta;
            cin >> delta;
            // No action needed
        } else if (token == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (token == "ALICE") {
            int cs1, v1, cs2, v2;
            cin >> cs1 >> v1 >> cs2 >> v2;
        } else if (token == "BOARD") {
            // k is unknown here; just consume rest of line
            string rest;
            getline(cin, rest);
        } else {
            if (token == "-1") return 0;
            string rest;
            getline(cin, rest);
        }
    }

    return 0;
}