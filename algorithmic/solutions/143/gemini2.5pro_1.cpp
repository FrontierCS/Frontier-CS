#include <iostream>
#include <string>
#include <vector>
#include <utility>
#include <cmath>
#include <algorithm>

// Reads RATES response from judge. Exits if judge sends -1.
std::pair<double, double> read_rates() {
    std::string token;
    std::cin >> token;
    if (token == "-1") {
        exit(0);
    }
    double w, d;
    std::cin >> w >> d;
    return {w, d};
}

// Asks judge for equity estimation.
std::pair<double, double> get_rates(int t) {
    std::cout << "RATE " << t << std::endl;
    return read_rates();
}

void decide_action(int r, long long a, long long P) {
    if (a == 0) {
        std::cout << "ACTION CHECK" << std::endl;
        return;
    }

    const int t_vals[] = {0, 30, 60, 90, 120};
    auto rates = get_rates(t_vals[r]);
    double eq = rates.first + rates.second / 2.0;

    const double val_thresh[] = {0, 0.65, 0.70, 0.75, 0.80};
    const double bluff_thresh[] = {0, 0.0, 0.30, 0.25, 0.0}; 

    if (r == 1) { // Preflop
        if (eq > val_thresh[r]) {
            long long raise_amt = std::min(a, 15LL);
            std::cout << "ACTION RAISE " << raise_amt << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 2 || r == 3) { // Flop & Turn
        if (eq > val_thresh[r]) {
            long long raise_amt = round(P * 0.75);
            raise_amt = std::min(a, std::max(1LL, raise_amt));
            std::cout << "ACTION RAISE " << raise_amt << std::endl;
        } else if (eq < bluff_thresh[r]) {
            long long raise_amt = P;
            raise_amt = std::min(a, std::max(1LL, raise_amt));
            std::cout << "ACTION RAISE " << raise_amt << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else { // r == 4, River
        if (eq > 0.95) {
            std::cout << "ACTION RAISE " << a << std::endl;
        } else if (eq > val_thresh[r]) {
            long long raise_amt = P;
            raise_amt = std::min(a, std::max(1LL, raise_amt));
            std::cout << "ACTION RAISE " << raise_amt << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
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

    for (int h = 1; h <= G; ++h) {
        bool hand_over = false;
        while (!hand_over) {
            std::string token;
            std::cin >> token;
            if (token == "-1") {
                return 0;
            }

            if (token == "STATE") {
                int h_read, r, k;
                long long a, b, P;
                std::cin >> h_read >> r >> a >> b >> P >> k;
                
                std::string dummy_str;
                int dummy_int;
                // ALICE c1 v1 c2 v2
                std::cin >> dummy_str >> dummy_int >> dummy_int >> dummy_int >> dummy_int;
                // BOARD ...
                std::cin >> dummy_str;
                std::string rest_of_board;
                getline(std::cin, rest_of_board);

                decide_action(r, a, P);
            } else if (token == "RESULT") {
                long long delta;
                std::cin >> delta;
                hand_over = true;
            } else { // Can be OPP or SCORE
                std::string dummy_line;
                getline(std::cin, dummy_line);
            }
        }
    }

    return 0;
}