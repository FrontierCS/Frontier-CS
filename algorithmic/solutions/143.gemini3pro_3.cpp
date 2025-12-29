#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int G;
    if (!(cin >> G)) return 0;

    long long total_budget = 3000000;
    long long used_budget = 0;

    for (int h = 1; h <= G; ++h) {
        // Hand loop
        while (true) {
            string token;
            cin >> token;
            if (token == "-1") return 0;
            if (token == "SCORE") {
                double s; cin >> s;
                return 0;
            }
            if (token == "RESULT") {
                int delta; cin >> delta;
                break; // Hand finished
            }
            
            // Expected token is "STATE" at the start of a decision node
            // If "Judge:" or similar prefixes appear in a different protocol version, 
            // the simple cin >> token handles skipping whitespace, but we assume
            // "STATE" is the first relevant token as per problem description.

            int hand_id, r, stack_a, stack_b, pot, k;
            cin >> hand_id >> r >> stack_a >> stack_b >> pot >> k;

            string lbl; cin >> lbl; // "ALICE"
            int s1, v1, s2, v2;
            cin >> s1 >> v1 >> s2 >> v2;

            cin >> lbl; // "BOARD"
            vector<pair<int,int>> board(k);
            for(int i=0; i<k; ++i) {
                cin >> board[i].first >> board[i].second;
            }

            // Decision Logic
            // Strategy: 
            // - Preflop (r=1): Check. Conserves budget and realizes equity for free.
            // - Postflop (r>1): Use RATE to estimate hand strength against random hand.
            //   - Exploit opponent's assumption of "Random Hand" for Alice.
            
            string action_str = "CHECK";
            int raise_amt = 0;

            if (r > 1) {
                // Determine sample size
                // Budget 3M for 10k hands => 300 per hand.
                // 3 postflop streets => 100 per decision is safe.
                int t = 100;
                
                if (total_budget - used_budget >= t) {
                    cout << "RATE " << t << endl;
                    used_budget += t;
                    
                    string r_lbl; cin >> r_lbl; // "RATES"
                    double w, d; cin >> w >> d;
                    double E = w + d/2.0;
                    
                    // Betting Strategy based on Equity E
                    // - E < 0.6: Check.
                    // - 0.6 <= E < 0.85: Raise Pot. (Bob calls wide thinking he has equity)
                    // - 0.85 <= E < 0.95: Raise 1/2 Pot. (Value bet)
                    // - E >= 0.95: Raise 1/4 Pot. (Induce call from weak range)
                    
                    if (stack_a > 0 && E >= 0.6) {
                        action_str = "RAISE";
                        if (E < 0.85) {
                            raise_amt = pot; 
                        } else if (E < 0.95) {
                            raise_amt = pot / 2;
                        } else {
                            raise_amt = pot / 4;
                        }
                        
                        raise_amt = max(1, raise_amt);
                        raise_amt = min(raise_amt, stack_a); // Cap at stack
                        
                        // Fallback if calculated raise is invalid
                        if (raise_amt < 1) action_str = "CHECK";
                    }
                }
            }

            if (action_str == "RAISE") {
                cout << "ACTION RAISE " << raise_amt << endl;
            } else {
                cout << "ACTION CHECK" << endl;
            }

            // Read Opponent Response
            string opp_lbl; cin >> opp_lbl; // "OPP"
            string opp_act; cin >> opp_act;
            
            if (opp_act == "FOLD") {
                string res_lbl; cin >> res_lbl; // "RESULT"
                int delta; cin >> delta;
                break; // Hand ends
            } else if (opp_act == "CALL") {
                int val; cin >> val;
                if (r == 4) {
                    string res_lbl; cin >> res_lbl; // "RESULT"
                    int delta; cin >> delta;
                    break; // Hand ends
                }
            } else if (opp_act == "CHECK") {
                if (r == 4) {
                    string res_lbl; cin >> res_lbl; // "RESULT"
                    int delta; cin >> delta;
                    break; // Hand ends
                }
            }
        }
    }
    
    // Read final score if match ends normally
    string final_token;
    while(cin >> final_token) {
        if(final_token == "SCORE") {
            double s; cin >> s;
            break;
        }
    }

    return 0;
}