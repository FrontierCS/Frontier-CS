#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

// Global budget tracking
long long total_budget = 3000000;
long long used_budget = 0;

struct Card {
    int suit;
    int val;
};

int main() {
    // Optimize I/O operations; standard streams are used for interaction.
    // We must flush after every output. std::endl performs a flush.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int G;
    if (!(cin >> G)) return 0;

    int hand_id, round_num, my_stack, opp_stack, pot, num_comm_cards;
    vector<Card> my_cards;
    vector<Card> board_cards;

    // Main game loop
    while (true) {
        string token;
        cin >> token;
        
        // Handle stream failure or exit signal
        if (cin.fail() || token == "-1") break;

        if (token == "SCORE") {
            double score;
            cin >> score;
            break; // Match ended
        } else if (token == "RESULT") {
            int delta;
            cin >> delta;
            // Hand ended; wait for next STATE or SCORE
            continue;
        } else if (token == "OPP") {
            // Processing opponent's immediate response
            string action;
            cin >> action;
            if (action == "CALL") {
                int x;
                cin >> x;
            }
            // If action is CHECK or FOLD, no extra args.
            // After OPP line, we loop again to get the next STATE or RESULT.
            continue;
        } else if (token == "STATE") {
            // Read state details
            cin >> hand_id >> round_num >> my_stack >> opp_stack >> pot >> num_comm_cards;

            // Read Alice's cards
            string lbl;
            cin >> lbl; // "ALICE"
            my_cards.resize(2);
            cin >> my_cards[0].suit >> my_cards[0].val;
            cin >> my_cards[1].suit >> my_cards[1].val;

            // Read Board cards
            cin >> lbl; // "BOARD"
            board_cards.resize(num_comm_cards);
            for (int i = 0; i < num_comm_cards; ++i) {
                cin >> board_cards[i].suit >> board_cards[i].val;
            }

            // Strategy Implementation
            // We have a budget of 3,000,000 rollouts for G hands (up to 10,000).
            // Average budget per hand = 300. 
            // A hand has up to 4 betting rounds. 75 samples per round is a safe baseline.
            
            int samples = 75;
            // Ensure we don't exceed global budget
            if (used_budget + samples > total_budget) {
                samples = (int)(total_budget - used_budget);
            }

            double equity = 0.5; // Default assumption if no budget left
            
            if (samples > 0) {
                cout << "RATE " << samples << endl;
                string r_token;
                double w, d;
                cin >> r_token >> w >> d; // Expect "RATES w d"
                equity = w + d / 2.0;
                used_budget += samples;
            }

            // Decision Logic
            // The opponent is passive (checks to us).
            // She calls raises based on her equity against a random hand.
            // 
            // 1. Never FOLD: Since the opponent checks to us, we can always CHECK for free
            //    to realize our equity or reach showdown. Folding forfeits the pot needlessly.
            // 2. CHECK if equity is low (< 0.55). Bluffing is risky as opponent calls
            //    based on absolute strength against random, not relative to our range.
            // 3. RAISE if equity is high (> 0.55) to extract value.
            
            if (equity < 0.55) {
                cout << "ACTION CHECK" << endl;
            } else {
                long long raise_amt = 0;
                
                // Scale bet size with strength to maximize expected value
                // Opponent assumes we check future streets, so she might call loosely
                // if she feels ahead of random, or fold if behind.
                if (equity > 0.85) {
                    // Very strong: Raise big (2x Pot) to build pot
                    raise_amt = (long long)pot * 2;
                } else if (equity > 0.70) {
                    // Strong: Pot size
                    raise_amt = (long long)pot;
                } else {
                    // Marginal edge: Half pot
                    raise_amt = (long long)pot / 2;
                }

                // Ensure raise amount is valid
                if (raise_amt < 1) raise_amt = 1;
                if (raise_amt > my_stack) raise_amt = my_stack;

                cout << "ACTION RAISE " << raise_amt << endl;
            }
        }
    }

    return 0;
}