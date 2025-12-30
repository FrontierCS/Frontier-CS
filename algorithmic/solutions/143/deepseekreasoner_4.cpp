#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

struct Card {
    int suit;
    int value;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    cin >> G;

    const int default_samples = 50;
    long long total_samples_used = 0;
    const long long max_samples = 3000000;

    vector<Card> hole(2);
    vector<Card> board;
    board.reserve(5);

    for (int hand = 1; hand <= G; ++hand) {
        while (true) {
            string token;
            cin >> token;
            if (token == "-1") {
                return 0;
            }
            if (token == "STATE") {
                int h, r, a, b, P, k;
                cin >> h >> r >> a >> b >> P >> k;
                // read ALICE
                cin >> token; // "ALICE"
                cin >> hole[0].suit >> hole[0].value >> hole[1].suit >> hole[1].value;
                // read BOARD
                cin >> token; // "BOARD"
                board.resize(k);
                for (int i = 0; i < k; ++i) {
                    cin >> board[i].suit >> board[i].value;
                }

                // Estimate equity via RATE query if we have budget
                double eq = 0.5; // default
                int t = default_samples;
                if (total_samples_used + t > max_samples) {
                    t = max_samples - total_samples_used;
                }
                if (t > 0) {
                    cout << "RATE " << t << endl;
                    total_samples_used += t;
                    string rates;
                    cin >> rates; // should be "RATES"
                    double win_prob, tie_prob;
                    cin >> win_prob >> tie_prob;
                    eq = win_prob + 0.5 * tie_prob;
                }

                if (eq <= 0.5 || a == 0) {
                    cout << "ACTION CHECK" << endl;
                    string opp, opp_action;
                    cin >> opp >> opp_action; // OPP CHECK
                    if (r == 4) {
                        cin >> token; // RESULT
                        int delta;
                        cin >> delta;
                        break;
                    }
                } else {
                    // raise half pot, at least 1, at most a
                    int x = static_cast<int>(0.5 * P);
                    if (x < 1) x = 1;
                    if (x > a) x = a;
                    cout << "ACTION RAISE " << x << endl;
                    string opp, opp_action;
                    cin >> opp >> opp_action;
                    if (opp_action == "FOLD") {
                        cin >> token; // RESULT
                        int delta;
                        cin >> delta;
                        break;
                    } else if (opp_action == "CALL") {
                        int raised_x;
                        cin >> raised_x;
                        if (r == 4) {
                            cin >> token; // RESULT
                            int delta;
                            cin >> delta;
                            break;
                        }
                        // else continue to next round
                    }
                }
            } else if (token == "RESULT") {
                int delta;
                cin >> delta;
                break;
            } else if (token == "SCORE") {
                double score;
                cin >> score;
                return 0;
            }
        }
    }
    return 0;
}