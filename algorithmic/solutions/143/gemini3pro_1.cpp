#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Card structure
struct Card {
    int suit;
    int value; // 1..13 corresponding to 2..A
};

// Game state structure
struct State {
    int h; // Hand index
    int r; // Round
    int a; // Alice stack
    int b; // Bob stack
    int P; // Pot
    int k; // Board card count
};

State currentState;
Card aliceCards[2];
vector<Card> boardCards;
int G; // Total hands
long long total_samples_used = 0;
const long long MAX_SAMPLES = 3000000;

// Simple preflop strength evaluator
// Returns true if the hand is strong enough to value bet preflop
bool isStrongPreflop() {
    Card c1 = aliceCards[0];
    Card c2 = aliceCards[1];
    // Sort so c1 is high card
    if (c1.value < c2.value) swap(c1, c2);
    
    // Values mapping: 1->2, ..., 12->K, 13->A
    
    // Pairs: Raise 88+
    // 7 corresponds to 8 (since 1 is 2, 2 is 3... 7 is 8)
    if (c1.value == c2.value) {
        return c1.value >= 7; 
    }
    
    bool suited = (c1.suit == c2.suit);
    
    // High Cards
    // Ace High
    if (c1.value == 13) { 
        if (c2.value >= 9) return true; // AT+ (9 is T)
        if (suited && c2.value >= 8) return true; // A9s+ (8 is 9)
    }
    // King High
    if (c1.value == 12) { 
        if (c2.value >= 11) return true; // KQ (11 is Q)
        if (suited && c2.value >= 10) return true; // KJs+ (10 is J)
    }
    
    return false;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read total number of hands
    if (!(cin >> G)) return 0;

    string line;
    // Main loop driving the interaction
    while (cin >> line) {
        if (line == "-1") return 0; // Error or terminate
        if (line == "SCORE") {
            double w; cin >> w;
            return 0; // End of match
        }
        
        if (line == "STATE") {
            cin >> currentState.h >> currentState.r >> currentState.a >> currentState.b >> currentState.P >> currentState.k;
        } else if (line == "ALICE") {
            cin >> aliceCards[0].suit >> aliceCards[0].value >> aliceCards[1].suit >> aliceCards[1].value;
        } else if (line == "BOARD") {
            boardCards.clear();
            for (int i = 0; i < currentState.k; ++i) {
                Card c;
                cin >> c.suit >> c.value;
                boardCards.push_back(c);
            }

            // --- Decision Logic ---
            
            // If we have no chips, we must check (cannot raise)
            if (currentState.a == 0) {
                 cout << "ACTION CHECK" << endl;
            } 
            // Preflop Strategy
            else if (currentState.r == 1) { 
                if (isStrongPreflop()) {
                    // Raise for value. Pot size is usually 10.
                    int amt = 10; 
                    if (amt > currentState.a) amt = currentState.a;
                    cout << "ACTION RAISE " << amt << endl;
                } else {
                    // Check weak/medium hands to see flop for free
                    cout << "ACTION CHECK" << endl;
                }
            } 
            // Postflop Strategy
            else { 
                // Budget Management
                long long remaining = MAX_SAMPLES - total_samples_used;
                long long hands_left = G - currentState.h + 1;
                if (hands_left < 1) hands_left = 1;

                int base = 50; 
                if (currentState.r == 4) base = 100; // More samples on River
                
                // Scale down if running low on budget
                // Assume approx 3 queries per hand remaining
                if (remaining < hands_left * 40) { 
                   base = (int)(remaining / (hands_left * 3.0));
                }
                if (base < 0) base = 0;
                
                double w = 0, d = 0;
                bool info = false;
                
                // Query Judge if budget allows
                if (base > 0) {
                    cout << "RATE " << base << endl;
                    total_samples_used += base;
                    string resp; cin >> resp;
                    if (resp == "RATES") {
                        cin >> w >> d;
                        info = true;
                    } else if (resp == "-1") return 0;
                }
                
                if (info) {
                    double eq = w + d/2.0;
                    double thresh = 0.6;
                    // Lower threshold on river for thin value
                    if (currentState.r == 4) thresh = 0.55;

                    if (eq > thresh) {
                        int amt = currentState.P; // Pot sized bet
                        
                        // Sizing tweak: if super strong, bet smaller to induce calls?
                        // Or just standard value.
                        if (eq > 0.85) amt = currentState.P / 2;
                        
                        if (amt > currentState.a) amt = currentState.a;
                        if (amt < 1) amt = 1;
                        cout << "ACTION RAISE " << amt << endl;
                    } else {
                        cout << "ACTION CHECK" << endl;
                    }
                } else {
                    // No info (budget exhausted), play safe
                    cout << "ACTION CHECK" << endl;
                }
            }

        } else if (line == "OPP") {
            string act; cin >> act;
            if (act == "CALL") {
                int x; cin >> x;
            }
            // If FOLD, next is RESULT. If CHECK/CALL, next is STATE or RESULT.
        } else if (line == "RESULT") {
            int delta; cin >> delta;
            // Hand ends
        }
    }
    return 0;
}