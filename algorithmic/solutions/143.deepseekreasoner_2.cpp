#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cout.tie(0);

    int G;
    cin >> G;
    if (G == -1) return 0;
    long long total_samples = 0;
    const long long MAX_SAMPLES = 3000000;

    for (int hand = 1; hand <= G; hand++) {
        while (true) {
            string token;
            cin >> token;
            if (token == "-1") return 0;
            if (token == "STATE") {
                int r, a, b, P, k;
                int hand_idx;
                cin >> hand_idx >> r >> a >> b >> P >> k;
                // Read ALICE line
                cin >> token; // "ALICE"
                int c1, v1, c2, v2;
                cin >> c1 >> v1 >> c2 >> v2;
                // Read BOARD line
                cin >> token; // "BOARD"
                vector<pair<int,int>> board;
                for (int i = 0; i < k; i++) {
                    int suit, val;
                    cin >> suit >> val;
                    board.emplace_back(suit, val);
                }

                // Determine number of samples for RATE
                int t = 0;
                if (r <= 2) t = 50;
                else t = 100;
                if (total_samples + t > MAX_SAMPLES) {
                    t = MAX_SAMPLES - total_samples;
                }
                double win_prob = 0.0, tie_prob = 0.0;
                if (t > 0) {
                    total_samples += t;
                    cout << "RATE " << t << endl;
                    cout.flush();
                    string rates;
                    cin >> rates; // "RATES"
                    cin >> win_prob >> tie_prob;
                }

                double EQ;
                if (t == 0) {
                    EQ = 0.5; // default neutral if no samples left
                } else {
                    EQ = win_prob + 0.5 * tie_prob;
                }

                // Decision heuristic
                if (EQ < 0.1 && r == 1) {
                    cout << "ACTION FOLD" << endl;
                } else if (EQ > 0.7) {
                    int x = min(a, P);
                    if (x < 1) x = 1;
                    cout << "ACTION RAISE " << x << endl;
                } else if (EQ < 0.3) {
                    int x = min(a, 2*P);
                    if (x < 1) x = 1;
                    cout << "ACTION RAISE " << x << endl;
                } else {
                    cout << "ACTION CHECK" << endl;
                }
                cout.flush();

                // Read opponent's response
                string opp;
                cin >> opp;
                if (opp == "-1") return 0;
                if (opp == "OPP") {
                    string act;
                    cin >> act;
                    if (act == "CHECK") {
                        if (r == 4) {
                            string res;
                            cin >> res; // "RESULT"
                            int delta;
                            cin >> delta;
                            break; // hand ends
                        }
                        // else continue to next round
                    } else if (act == "FOLD") {
                        string res;
                        cin >> res; // "RESULT"
                        int delta;
                        cin >> delta;
                        break;
                    } else if (act == "CALL") {
                        int raised;
                        cin >> raised;
                        if (r == 4) {
                            string res;
                            cin >> res; // "RESULT"
                            int delta;
                            cin >> delta;
                            break;
                        }
                        // else continue to next round
                    }
                } else if (opp == "RESULT") {
                    int delta;
                    cin >> delta;
                    break;
                } else if (opp == "SCORE") {
                    double W;
                    cin >> W;
                    return 0;
                }
            } else if (token == "RESULT") {
                int delta;
                cin >> delta;
                break;
            } else if (token == "SCORE") {
                double W;
                cin >> W;
                return 0;
            }
        }
    }
    // Read final SCORE
    string token;
    cin >> token;
    if (token == "SCORE") {
        double W;
        cin >> W;
    } else if (token == "-1") return 0;
    return 0;
}