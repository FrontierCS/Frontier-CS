#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <tuple>

long long h_ll;
int r, a, b, P, k;
std::vector<std::pair<int, int>> my_cards;
std::vector<std::pair<int, int>> board_cards;

void parse_state() {
    long long h_in;
    std::cin >> h_in >> r >> a >> b >> P >> k;
    h_ll = h_in;
}

void parse_my_cards() {
    std::string token;
    std::cin >> token; // "ALICE"
    my_cards.resize(2);
    std::cin >> my_cards[0].first >> my_cards[0].second;
    std::cin >> my_cards[1].first >> my_cards[1].second;
}

void parse_board_cards() {
    std::string token;
    std::cin >> token; // "BOARD"
    board_cards.resize(k);
    for (int i = 0; i < k; ++i) {
        std::cin >> board_cards[i].first >> board_cards[i].second;
    }
}

std::pair<double, double> get_rates(int t) {
    std::cout << "RATE " << t << std::endl;
    std::string token;
    double w, d;
    std::cin >> token; // "RATES"
    if (token == "-1") exit(0);
    std::cin >> w >> d;
    return {w, d};
}

void do_raise(int amount) {
    if (a <= 0) {
        std::cout << "ACTION CHECK" << std::endl;
        return;
    }
    int raise_amount = std::min(a, std::max(1, amount));
    std::cout << "ACTION RAISE " << raise_amount << std::endl;
}

void make_decision() {
    double w, d;
    if (r == 1) { // Preflop
        std::tie(w, d) = get_rates(50);
        double equity = w + d / 2.0;
        if (equity > 0.60) {
            do_raise(10);
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 2) { // Flop
        std::tie(w, d) = get_rates(75);
        double equity = w + d / 2.0;
        if (equity > 0.85) {
            do_raise(P);
        } else if (equity > 0.65) {
            do_raise(P / 2);
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 3) { // Turn
        std::tie(w, d) = get_rates(75);
        double equity = w + d / 2.0;
        if (equity > 0.9) {
            do_raise(a);
        } else if (equity > 0.7) {
            do_raise(P);
        } else if (equity < 0.2 && h_ll % 5 == 0) { // Bluff
            do_raise(P * 3 / 4);
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    } else if (r == 4) { // River
        std::tie(w, d) = get_rates(100);
        double equity = w + d / 2.0;
        if (equity > 0.9) {
            do_raise(a);
        } else if (equity > 0.75) {
            do_raise(P);
        } else if (equity > 0.5) {
            do_raise(P / 2);
        } else if (equity < 0.15 && h_ll % 4 == 0) { // Bluff
            do_raise(P);
        } else {
            std::cout << "ACTION CHECK" << std::endl;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int G;
    std::string first_token;
    std::cin >> first_token;

    if (first_token == "-1") return 0;
    try {
        G = std::stoi(first_token);
    } catch (...) {
        return 0;
    }
    
    for (int i = 0; i < G; ++i) {
        while (true) {
            std::string token;
            std::cin >> token; // "STATE"
            if (token == "-1") return 0;
            if (token != "STATE") { // Should be SCORE or error
                return 0;
            }
            
            parse_state();
            parse_my_cards();
            parse_board_cards();
            
            make_decision();
            
            std::cin >> token; // "OPP" or "RESULT"
            if (token == "-1") return 0;
            
            if (token == "OPP") {
                std::string action;
                std::cin >> action; // "CHECK", "FOLD", "CALL"
                if (action == "-1") return 0;

                if (action == "FOLD") {
                    std::cin >> token; // "RESULT"
                    if (token == "-1") return 0;
                    int delta;
                    std::cin >> delta;
                    break; 
                } else if (action == "CALL") {
                    int call_amount;
                    std::cin >> call_amount;
                    if (r == 4) { 
                        std::cin >> token; // "RESULT"
                        if (token == "-1") return 0;
                        int delta;
                        std::cin >> delta;
                        break;
                    }
                } else { // CHECK
                    if (r == 4) {
                        std::cin >> token; // "RESULT"
                        if (token == "-1") return 0;
                        int delta;
                        std::cin >> delta;
                        break;
                    }
                }
            } else if (token == "RESULT") {
                int delta;
                std::cin >> delta;
                break;
            }
        }
    }

    return 0;
}