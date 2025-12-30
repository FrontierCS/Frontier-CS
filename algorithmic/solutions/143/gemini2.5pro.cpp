#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cmath>

void decide_action() {
    // STATE variables
    int h, r;
    long long a, b, P;
    int k;
    std::cin >> h >> r >> a >> b >> P >> k;

    // ALICE cards (unused, but must be read)
    std::string alice_token;
    int c1, v1, c2, v2;
    std::cin >> alice_token >> c1 >> v1 >> c2 >> v2;

    // BOARD cards (unused, but must be read)
    std::string board_token;
    std::cin >> board_token;
    std::string board_cards_line;
    std::getline(std::cin, board_cards_line);

    // Decide on number of rollouts for RATE query based on the round
    int t;
    if (r == 1) t = 75;
    else if (r == 2) t = 100;
    else if (r == 3) t = 100;
    else t = 25; // r == 4

    // Query for equity
    std::cout << "RATE " << t << std::endl;

    // Read judge's response
    std::string rates_token;
    double w, d;
    std::cin >> rates_token >> w >> d;

    double E = w + d / 2.0;
    long long x = 0;

    // Strategy based on round and equity
    if (r == 1) { // Preflop
        if (E > 0.62) {
            x = 5;
        }
    } else if (r == 2) { // Flop
        if (E > 0.8) {
            x = P;
        } else if (E > 0.65) {
            x = P * 2 / 3;
        } else if (E > 0.5) {
            x = P / 2;
        }
    } else if (r == 3) { // Turn
        if (E > 0.85) {
            x = a;
        } else if (E > 0.7) {
            x = P;
        } else if (E > 0.55) {
            x = P * 2 / 3;
        }
    } else { // r == 4, River
        if (E > 0.9) {
            x = a;
        } else if (E > 0.75) {
            x = P;
        } else if (E > 0.5) {
            x = P / 2;
        } else if (E < 0.2) {
            x = P;
        }
    }

    // Ensure raise amount is valid (1 <= x <= stack)
    x = std::min(x, a);
    
    if (x >= 1) {
        std::cout << "ACTION RAISE " << x << std::endl;
    } else {
        std::cout << "ACTION CHECK" << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int G;
    std::cin >> G;
    if (G == -1) {
        return 0;
    }

    std::string token;
    while (std::cin >> token) {
        if (token == "STATE") {
            decide_action();
        } else if (token == "SCORE") {
            break;
        } else if (token == "-1") {
            break;
        }
    }

    return 0;
}