#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <cassert>

using namespace std;

int main() {
    int G;
    cin >> G;
    int remaining_budget = 3000000;
    for (int hand = 1; hand <= G; hand++) {
        bool hand_in_progress = true;
        int current_round = 0;
        while (hand_in_progress) {
            string token;
            cin >> token;
            if (token == "STATE") {
                int h, r, a, b, P, k;
                cin >> h >> r >> a >> b >> P >> k;
                current_round = r;
                // Read ALICE line
                string alice;
                cin >> alice;
                assert(alice == "ALICE");
                int c1, v1, c2, v2;
                cin >> c1 >> v1 >> c2 >> v2;
                // Read BOARD line
                string board;
                cin >> board;
                assert(board == "BOARD");
                // Read k cards if any
                for (int i = 0; i < k; i++) {
                    int s, val;
                    cin >> s >> val;
                }
                // Decide action
                // Query RATE
                int t = 75; // default
                if (t > remaining_budget) {
                    t = remaining_budget;
                }
                double w = 0.0, d = 0.0;
                if (t > 0) {
                    cout << "RATE " << t << endl;
                    remaining_budget -= t;
                    string rates;
                    cin >> rates;
                    if (rates == "-1") return 0;
                    assert(rates == "RATES");
                    cin >> w >> d;
                } else {
                    // no budget, default to check
                    cout << "ACTION CHECK" << endl;
                    continue;
                }
                double eq_us = w + d/2.0;
                if (eq_us > 0.5) {
                    double eq_her = 1.0 - eq_us;
                    double x_thresh = (eq_her * P) / (2.0 * eq_us - 1.0);
                    if (a >= x_thresh) {
                        int x = (int)ceil(x_thresh);
                        if (x < 1) x = 1;
                        if (x > a) x = a;
                        cout << "ACTION RAISE " << x << endl;
                    } else {
                        cout << "ACTION RAISE " << a << endl;
                    }
                } else {
                    cout << "ACTION CHECK" << endl;
                }
            } else if (token == "OPP") {
                string opp_action;
                cin >> opp_action;
                if (opp_action == "CHECK") {
                    if (current_round == 4) {
                        // Next should be RESULT
                        string next;
                        cin >> next;
                        if (next == "-1") return 0;
                        if (next == "RESULT") {
                            int delta;
                            cin >> delta;
                            hand_in_progress = false;
                        }
                    }
                    // else, continue to next STATE
                } else if (opp_action == "FOLD") {
                    // Next should be RESULT
                    string next;
                    cin >> next;
                    if (next == "-1") return 0;
                    if (next == "RESULT") {
                        int delta;
                        cin >> delta;
                        hand_in_progress = false;
                    }
                } else if (opp_action == "CALL") {
                    int x;
                    cin >> x;
                    if (current_round == 4) {
                        string next;
                        cin >> next;
                        if (next == "-1") return 0;
                        if (next == "RESULT") {
                            int delta;
                            cin >> delta;
                            hand_in_progress = false;
                        }
                    }
                    // else, continue
                }
            } else if (token == "RESULT") {
                int delta;
                cin >> delta;
                hand_in_progress = false;
            } else if (token == "SCORE") {
                double score;
                cin >> score;
                return 0;
            } else if (token == "-1") {
                return 0;
            }
        }
    }
    return 0;
}