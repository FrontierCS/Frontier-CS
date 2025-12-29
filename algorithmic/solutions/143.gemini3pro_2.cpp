#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O operations for speed, but ensure explicit flushes.
    // cin.tie(NULL) unties cin from cout, so we must flush cout manually (endl does this).
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int G;
    // Read number of hands. If this fails, exit.
    if (!(cin >> G)) return 0;

    // Main game loop
    while (true) {
        string token;
        cin >> token;

        // Check for end of input or error signal
        if (cin.fail() || token == "") break;
        if (token == "-1") return 0;

        if (token == "SCORE") {
            // Match finished, read final score
            double score; cin >> score;
            break;
        }
        else if (token == "RESULT") {
            // Hand finished, read profit/loss for this hand
            int delta; cin >> delta;
            // The loop continues to the next hand (or SCORE)
        }
        else if (token == "STATE") {
            // Parse game state
            int h, r, a, b, P, k;
            cin >> h >> r >> a >> b >> P >> k;

            // Read Alice's hole cards
            string alice_dummy; cin >> alice_dummy; // "ALICE"
            int ac1, av1, ac2, av2;
            cin >> ac1 >> av1 >> ac2 >> av2;

            // Read Community cards (Board)
            string board_dummy; cin >> board_dummy; // "BOARD"
            for(int i = 0; i < k; ++i) {
                int s, v; cin >> s >> v;
            }

            // Use Monte Carlo simulation via RATE query to estimate equity.
            // Global budget is 3,000,000 for 10,000 hands (avg 300/hand).
            // We allocate samples based on street importance.
            // Preflop (r=1) and Flop (r=2): 40 samples (early estimation).
            // Turn (r=3): 80 samples.
            // River (r=4): 100 samples (critical decision).
            // Total max per hand = 260, well within safe limits.
            int t = 40; 
            if (r == 3) t = 80;
            if (r == 4) t = 100;

            cout << "RATE " << t << endl;

            // Read simulation results
            string rates_dummy; cin >> rates_dummy; // "RATES"
            double w, d; cin >> w >> d;
            double equity = w + d * 0.5;

            // Decision Logic: Exploitative Value Betting
            // Since Bob calls based on pot odds against a random hand, 
            // we value bet when our equity is high.
            // We avoid pure bluffing as checking down is +EV due to dead money in pot.
            
            string action = "CHECK";
            int raise_amt = 0;

            if (equity > 0.6) {
                double factor = 0.0;
                if (equity > 0.85) factor = 1.0;       // Monster: Bet Pot
                else if (equity > 0.75) factor = 0.75; // Very Strong: 3/4 Pot
                else if (equity > 0.60) factor = 0.5;  // Strong: 1/2 Pot
                
                if (factor > 0) {
                    int x = (int)(P * factor);
                    if (x < 1) x = 1; // Minimum raise is 1 chip
                    if (x > a) x = a; // Cannot raise more than stack
                    
                    if (a > 0) { // Can only raise if we have chips
                        action = "RAISE";
                        raise_amt = x;
                    }
                }
            }

            // Output decision
            if (action == "RAISE") {
                cout << "ACTION RAISE " << raise_amt << endl;
            } else {
                cout << "ACTION CHECK" << endl;
            }

            // Handle Judge's immediate response to our action
            string opp_lbl; cin >> opp_lbl; // Should be "OPP" or error
            if (opp_lbl == "-1") return 0;
            
            // Response format: OPP CHECK, OPP FOLD, or OPP CALL x
            string opp_act; cin >> opp_act;
            if (opp_act == "CALL") {
                int val; cin >> val; // Consume the call amount
            }
            // If OPP CHECK or OPP FOLD, no extra arguments follow on this line.
            // The loop then continues to read the next token (STATE or RESULT).
        }
    }

    return 0;
}