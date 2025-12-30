#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cstdlib>
#include <ctime>
#include <cmath>
#include <algorithm>

// Strategy parameters
// Indexed by round number (1-4). Index 0 is unused.
const int T_SAMPLES[] = {0, 20, 40, 80, 150};
const double E_VAL_THRESH[] = {0, 0.62, 0.67, 0.72, 0.85};
const double E_BLUFF_THRESH[] = {0, 1.0, 0.33, 0.28, 1.0}; // No bluff preflop/river
const double P_BLUFF[] = {0, 0.0, 0.15, 0.12, 0.0};
const double VAL_BET_SIZE_FRAC[] = {0, 0, 0.7, 0.8, 1.0}; // River is pot-sized
const double BLUFF_BET_SIZE_FRAC[] = {0, 0, 0.9, 1.1, 0};

// Helper to query RATE from judge
std::pair<double, double> query_rate(int t) {
    std::cout << "RATE " << t << std::endl;
    std::string line;
    if (!std::getline(std::cin, line) || line == "-1") {
        exit(0);
    }
    std::stringstream ss(line);
    std::string token;
    ss >> token;
    if (token == "RATES") {
        double w, d;
        ss >> w >> d;
        return {w, d};
    }
    exit(0); // Protocol violation or error
}

void decide_and_act(int r, int a, int P) {
    if (a == 0) {
        std::cout << "ACTION CHECK" << std::endl;
        return;
    }

    int samples = T_SAMPLES[r];
    std::pair<double, double> rates = query_rate(samples);
    double w = rates.first;
    double d = rates.second;
    double E = w + 0.5 * d;

    if (r == 1) { // Preflop
        if (E > E_VAL_THRESH[r]) {
            int raise_amount = std::min(a, 10);
            std::cout << "ACTION RAISE " << raise_amount << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 2 || r == 3) { // Flop and Turn
        if (E > E_VAL_THRESH[r]) {
            int raise_amount = std::max(1, std::min(a, (int)round(P * VAL_BET_SIZE_FRAC[r])));
            std::cout << "ACTION RAISE " << raise_amount << std::endl;
        } else if (E < E_BLUFF_THRESH[r]) {
            double bluff_roll = (double)rand() / RAND_MAX;
            if (bluff_roll < P_BLUFF[r]) {
                int raise_amount = std::max(1, std::min(a, (int)round(P * BLUFF_BET_SIZE_FRAC[r])));
                std::cout << "ACTION RAISE " << raise_amount << std::endl;
            } else {
                std::cout << "ACTION CHECK" << std::endl;
            }
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 4) { // River
        if (E > E_VAL_THRESH[r]) {
            int raise_amount = std::max(1, std::min(a, P));
            std::cout << "ACTION RAISE " << raise_amount << std::endl;
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(0));

    std::string line;
    if (!std::getline(std::cin, line) || line == "-1") return 0;
    int G;
    try {
        G = std::stoi(line);
    } catch(...) {
        return 0;
    }

    while (std::getline(std::cin, line)) {
        if (line == "-1") return 0;
        if (line.empty()) continue;

        std::stringstream ss(line);
        std::string token;
        ss >> token;

        if (token == "SCORE") break;
        if (token != "STATE") continue;

        int h, r, a, b, P, k;
        ss >> h >> r >> a >> b >> P >> k;

        // Consume ALICE and BOARD lines; we don't need to parse card data
        if (!std::getline(std::cin, line) || line == "-1") return 0; // ALICE
        if (!std::getline(std::cin, line) || line == "-1") return 0; // BOARD
        
        decide_and_act(r, a, P);
    }
    return 0;
}