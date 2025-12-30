#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdlib>
#include <ctime>

// Global state variables, to be updated each time a STATE is read
int h_idx, r, a, b, P, k;
double w, d;

// My hole cards and board cards
int my_c1, my_v1, my_c2, my_v2;
std::vector<int> board_cards;

// Strategy parameters
const std::vector<int> t_samples = {0, 70, 100, 120, 150};
const std::vector<std::vector<double>> thresholds = {
    {}, // r=0 (unused)
    {0.6, 0.7, 0.85},   // r=1 (preflop)
    {0.55, 0.7, 0.85},  // r=2 (flop)
    {0.5, 0.65, 0.8},   // r=3 (turn)
    {0.5, 0.6, 0.8}     // r=4 (river)
};
const std::vector<int> bluff_probs = {0, 20, 15, 10, 5};
const double bluff_equity_thresh = 0.45;

void read_state_and_cards() {
    // Assumes "STATE" token has been read
    std::cin >> h_idx >> r >> a >> b >> P >> k;
    
    std::string token;
    
    std::cin >> token; // ALICE
    if (token == "-1") exit(0);
    std::cin >> my_c1 >> my_v1 >> my_c2 >> my_v2;

    std::cin >> token; // BOARD
    if (token == "-1") exit(0);
    board_cards.resize(2 * k);
    for (int i = 0; i < 2 * k; ++i) {
        std::cin >> board_cards[i];
    }
}

void get_rates() {
    if (r < 1 || r > 4) return;
    int t = t_samples[r];
    std::cout << "RATE " << t << std::endl;
    std::string token;
    std::cin >> token; // RATES
    if (token == "-1") exit(0);
    std::cin >> w >> d;
}

bool should_bluff(double E) {
    if (a == 0) return false;
    if (r > 0 && r < bluff_probs.size() && E < bluff_equity_thresh) {
        if (rand() % 100 < bluff_probs[r]) {
            return true;
        }
    }
    return false;
}

void play_one_hand() {
    std::string token;
    std::cin >> token; // The first "STATE" of the hand
    if (token == "-1") exit(0);

    read_state_and_cards();

    while (true) {
        get_rates();
        
        double E = w + d / 2.0;
        
        double T1 = thresholds[r][0];
        double T2 = thresholds[r][1];
        double T3 = thresholds[r][2];
        
        int raise_amt = 0;
        std::string action_str = "CHECK";

        if (a > 0) {
            if (E > T3) {
                action_str = "RAISE";
                raise_amt = a;
            } else if (E > T2) {
                action_str = "RAISE";
                raise_amt = std::min(a, std::max(1, P));
            } else if (E > T1) {
                action_str = "RAISE";
                raise_amt = std::min(a, std::max(1, P / 2));
            } else { // E <= T1
                if (should_bluff(E)) {
                    action_str = "RAISE";
                    raise_amt = std::min(a, std::max(1, P / 2));
                }
            }
        }
        
        if (action_str == "RAISE") {
            std::cout << "ACTION RAISE " << raise_amt << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }

        std::cin >> token; // "OPP"
        if (token == "-1") exit(0);

        std::string opp_action;
        std::cin >> opp_action;
        
        if (opp_action == "CALL") {
            int call_amt;
            std::cin >> call_amt;
        }

        if (opp_action == "FOLD" || r == 4) {
            std::cin >> token; // "RESULT"
            if (token == "-1") exit(0);
            int delta;
            std::cin >> delta;
            return; // Hand is over
        }

        // Hand continues, read next state
        std::cin >> token; // "STATE"
        if (token == "-1") exit(0);
        read_state_and_cards();
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(0));
    
    int G;
    std::cin >> G;
    if (G == -1) return 0;

    for (int i = 0; i < G; ++i) {
        play_one_hand();
    }
    
    std::string token;
    double score_val;
    std::cin >> token; // "SCORE"
    if (token != "-1") {
        std::cin >> score_val;
    }

    return 0;
}