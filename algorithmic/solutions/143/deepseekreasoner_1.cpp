#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>
#include <string>
#include <set>

using namespace std;

struct Card {
    int suit;
    int val;
};

vector<vector<int>> combos_7_5;

void generate_combinations(int n, int k, int start, vector<int>& current, vector<vector<int>>& res) {
    if ((int)current.size() == k) {
        res.push_back(current);
        return;
    }
    for (int i = start; i < n; ++i) {
        current.push_back(i);
        generate_combinations(n, k, i+1, current, res);
        current.pop_back();
    }
}

// Returns a vector representing the rank of a 5-card hand.
// First element is -type (type 1=straight flush, ..., 9=high card).
// For straight/straight flush: second element is the high card of the straight.
// For others: then 5 tiebreaker values sorted by (multiplicity, value) descending.
vector<int> hand_rank_5(const vector<Card>& cards) {
    vector<int> values;
    vector<int> suits;
    for (Card c : cards) {
        int v = c.val;
        if (v == 1) v = 14; // treat Ace as 14 except for low straight
        values.push_back(v);
        suits.push_back(c.suit);
    }
    sort(values.begin(), values.end());

    bool flush = (suits[0] == suits[1] && suits[0] == suits[2] &&
                  suits[0] == suits[3] && suits[0] == suits[4]);

    bool straight = false;
    int high = 0;
    if (values[4] - values[0] == 4 && values[0] + 4 == values[4]) {
        straight = true;
        high = values[4];
    } else if (values[0] == 2 && values[1] == 3 && values[2] == 4 &&
               values[3] == 5 && values[4] == 14) {
        straight = true;
        high = 5; // Ace-low straight, high card is 5
    }

    if (straight && flush) {
        // straight flush
        return {-1, high};
    }

    // count frequencies
    map<int, int> freq;
    for (int v : values) freq[v]++;
    vector<pair<int, int>> freq_vec; // (multiplicity, value)
    for (auto& p : freq) freq_vec.push_back({p.second, p.first});
    sort(freq_vec.begin(), freq_vec.end(),
         [](const pair<int, int>& a, const pair<int, int>& b) {
             if (a.first != b.first) return a.first > b.first;
             return a.second > b.second;
         });

    int type;
    if (freq_vec[0].first == 4) {
        type = 2; // four of a kind
    } else if (freq_vec[0].first == 3 && freq_vec[1].first == 2) {
        type = 3; // full house
    } else if (flush) {
        type = 4; // flush
    } else if (straight) {
        type = 5; // straight
    } else if (freq_vec[0].first == 3) {
        type = 6; // three of a kind
    } else if (freq_vec[0].first == 2 && freq_vec[1].first == 2) {
        type = 7; // two pairs
    } else if (freq_vec[0].first == 2) {
        type = 8; // one pair
    } else {
        type = 9; // high card
    }

    vector<int> key;
    key.push_back(-type);
    if (type == 5 || type == 1) { // straight or straight flush already handled
        key.push_back(high);
    } else {
        // build tiebreaker list
        vector<int> tiebreakers;
        for (auto& p : freq_vec) {
            for (int i = 0; i < p.first; ++i) {
                tiebreakers.push_back(p.second);
            }
        }
        // tiebreakers size should be 5
        for (int v : tiebreakers) key.push_back(v);
    }
    return key;
}

// Returns the rank vector of the best 5-card hand from 7 cards.
vector<int> best_hand_rank(const vector<Card>& cards7) {
    vector<int> best_key = {-10, 0}; // sufficiently low
    for (const vector<int>& combo : combos_7_5) {
        vector<Card> five;
        for (int idx : combo) five.push_back(cards7[idx]);
        vector<int> key = hand_rank_5(five);
        if (key > best_key) best_key = key;
    }
    return best_key;
}

// Compute exact equity on the river (all 5 board cards known).
double compute_exact_equity(const vector<Card>& our_hole, const vector<Card>& board) {
    vector<Card> our_hand = our_hole;
    our_hand.insert(our_hand.end(), board.begin(), board.end());
    vector<int> our_key = best_hand_rank(our_hand);

    // Mark used cards
    bool used[4][14] = {false}; // suit 0..3, value 1..13
    for (Card c : our_hole) used[c.suit][c.val] = true;
    for (Card c : board) used[c.suit][c.val] = true;

    vector<Card> remaining;
    for (int s = 0; s < 4; ++s) {
        for (int v = 1; v <= 13; ++v) {
            if (!used[s][v]) remaining.push_back({s, v});
        }
    }

    int wins = 0, ties = 0;
    int n = remaining.size();
    for (int i = 0; i < n; ++i) {
        for (int j = i+1; j < n; ++j) {
            vector<Card> opp_hole = {remaining[i], remaining[j]};
            vector<Card> opp_hand = opp_hole;
            opp_hand.insert(opp_hand.end(), board.begin(), board.end());
            vector<int> opp_key = best_hand_rank(opp_hand);
            if (our_key > opp_key) wins++;
            else if (our_key == opp_key) ties++;
        }
    }
    int total = n * (n-1) / 2;
    return (wins + ties / 2.0) / total;
}

int desired_samples(int round) {
    switch (round) {
        case 1: return 50;
        case 2: return 100;
        case 3: return 150;
        default: return 0;
    }
}

int main() {
    // Precompute all 5-card combinations from 7 cards.
    vector<int> cur;
    generate_combinations(7, 5, 0, cur, combos_7_5);

    int G;
    cin >> G;
    if (G < 0) return 0;

    long long total_samples = 0;
    const long long MAX_SAMPLES = 3000000;

    for (int hand = 1; hand <= G; ++hand) {
        while (true) {
            string token;
            cin >> token;
            if (token == "-1") return 0;
            if (token != "STATE") return 0;

            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            cin >> token; // "ALICE"
            vector<Card> our_hole(2);
            for (int i = 0; i < 2; ++i) {
                int s, v; cin >> s >> v;
                our_hole[i] = {s, v};
            }

            cin >> token; // "BOARD"
            vector<Card> board;
            for (int i = 0; i < k; ++i) {
                int s, v; cin >> s >> v;
                board.push_back({s, v});
            }

            double E;
            if (r == 4 && k == 5) {
                // River: compute exact equity.
                E = compute_exact_equity(our_hole, board);
            } else {
                int t = desired_samples(r);
                if (total_samples + t > MAX_SAMPLES) t = MAX_SAMPLES - total_samples;
                if (t > 0) {
                    cout << "RATE " << t << endl;
                    total_samples += t;
                    string rates;
                    double w, d;
                    cin >> rates >> w >> d;
                    if (rates == "-1") return 0;
                    E = w + d / 2.0;
                } else {
                    E = 0.5; // fallback
                }
            }

            // Decision making
            double ev_check = a - 100 + P * E;
            double best_ev = ev_check;
            string action = "CHECK";
            int raise_amt = 0;

            if (E > 0.5) {
                double T = P * (1.0 - E) / (2.0 * E - 1.0);
                // Option 1: raise to trigger fold.
                int x_fold = (int)ceil(T);
                if (x_fold >= 1 && x_fold <= a) {
                    double ev_fold = a + P - 100;
                    if (ev_fold > best_ev) {
                        best_ev = ev_fold;
                        action = "RAISE";
                        raise_amt = x_fold;
                    }
                }
                // Option 2: raise to trigger call.
                int x_call = (int)floor(T - 1e-9);
                if (x_call > a) x_call = a;
                if (x_call >= 1) {
                    double ev_call = a - 100 + P * E + x_call * (2 * E - 1);
                    if (ev_call > best_ev) {
                        best_ev = ev_call;
                        action = "RAISE";
                        raise_amt = x_call;
                    }
                }
            }
            // If E <= 0.5, checking is best (already set).

            cout << "ACTION " << action;
            if (action == "RAISE") cout << " " << raise_amt;
            cout << endl;

            // Read opponent's response.
            cin >> token;
            if (token == "-1") return 0;
            if (token == "OPP") {
                cin >> token;
                if (token == "CHECK") {
                    if (r == 4) {
                        cin >> token; // "RESULT"
                        int delta; cin >> delta;
                        break; // hand over
                    }
                    // else continue to next round
                } else if (token == "FOLD") {
                    cin >> token; // "RESULT"
                    int delta; cin >> delta;
                    break;
                } else if (token == "CALL") {
                    int x; cin >> x;
                    if (r == 4) {
                        cin >> token; // "RESULT"
                        int delta; cin >> delta;
                        break;
                    }
                    // else continue
                }
            } else if (token == "RESULT") {
                int delta; cin >> delta;
                break;
            } else {
                return 0; // unexpected
            }
        } // end while hand
    } // end for hand

    // Read final SCORE line (ignore but consume).
    string token;
    cin >> token;
    // token could be "SCORE" or "-1"
    if (token == "-1") return 0;
    // else ignore

    return 0;
}