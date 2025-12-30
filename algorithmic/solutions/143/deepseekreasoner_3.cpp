#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

using namespace std;

long long RATE_BUDGET = 3000000;
int current_round;

double profit_check(double W, double D, double I, double O) {
    double L = 1 - W - D;
    return W * (O + 10) + L * (-I) + D * (O - I + 10) / 2.0;
}

void compute_SC(double W, double D, double I, double O, double& S, double& C) {
    C = 1 - 2 * W - D;   // = L - W
    S = (1 - W - D) * (I + 10) - W * O + D * (I - O + 10) / 2.0;
}

void process_state(const string& line) {
    istringstream iss(line);
    string token;
    iss >> token; // "STATE"
    int h, r, a, b, P, k;
    iss >> h >> r >> a >> b >> P >> k;
    current_round = r;

    // Read ALICE line
    string alice_line;
    getline(cin, alice_line);
    istringstream alice_iss(alice_line);
    string alice_token;
    alice_iss >> alice_token; // "ALICE"
    int c1, v1, c2, v2;
    alice_iss >> c1 >> v1 >> c2 >> v2;

    // Read BOARD line
    string board_line;
    getline(cin, board_line);
    // We ignore the board cards because we use RATE queries.

    double I = 100.0 - a;
    double O = 100.0 - b;

    // Determine sample count for RATE
    int t = 0;
    if (r == 1) t = 20;
    else if (r == 2) t = 40;
    else if (r == 3) t = 60;
    else t = 80;

    if (t > RATE_BUDGET) t = RATE_BUDGET;

    double W = 0.5, D = 0.0; // defaults
    if (t > 0) {
        cout << "RATE " << t << endl;
        RATE_BUDGET -= t;

        string rates_line;
        getline(cin, rates_line);
        istringstream rates_iss(rates_line);
        string rates_token;
        rates_iss >> rates_token; // "RATES"
        rates_iss >> W >> D;
    } else {
        // No budget left, use default action (CHECK) and return.
        cout << "ACTION CHECK" << endl;
        return;
    }

    double K = profit_check(W, D, I, O);
    double profit_fold_action = -I;
    double best_profit = K;
    string best_action = "CHECK";
    int best_x = 0;

    // Consider folding
    if (profit_fold_action > best_profit) {
        best_profit = profit_fold_action;
        best_action = "FOLD";
    }

    // Consider raising if we have at least 1 chip
    if (a >= 1) {
        double S, C;
        compute_SC(W, D, I, O, S, C);
        double x_threshold = 0.0;
        if (fabs(C) > 1e-12) {
            x_threshold = (-O - S) / C;
        }

        bool can_fold = false, can_call = false;
        int x_fold = 0, x_call = 0;

        const double eps = 1e-9;
        if (C > eps) {
            // Bob folds if x <= x_threshold
            if (x_threshold >= 1.0 - eps) {
                x_fold = 1; // smallest possible fold-inducing raise
                if (x_fold <= a) can_fold = true;
            }
            // Bob calls if x > x_threshold
            x_call = (int)floor(x_threshold) + 1;
            if (x_call >= 1 && x_call <= a) can_call = true;
        } else if (C < -eps) {
            // Bob folds if x >= x_threshold
            x_fold = (int)ceil(x_threshold);
            if (x_fold >= 1 && x_fold <= a) can_fold = true;
            // Bob calls if x < x_threshold
            x_call = (int)ceil(x_threshold) - 1;
            if (x_call >= 1 && x_call <= a) can_call = true;
        } else { // C == 0
            if (S > -O) { // Bob calls any raise
                can_call = true;
                x_call = 1;
            } else { // Bob folds any raise
                can_fold = true;
                x_fold = 1;
            }
        }

        // Evaluate fold-inducing raise
        if (can_fold) {
            double profit = O + 10.0; // P_fold
            if (profit > best_profit) {
                best_profit = profit;
                best_action = "RAISE";
                best_x = x_fold;
            }
        }

        // Evaluate call-inducing raise
        if (can_call) {
            double edge = 2 * W + D - 1; // W - L
            double profit = K + x_call * edge;
            if (profit > best_profit) {
                best_profit = profit;
                best_action = "RAISE";
                best_x = x_call;
            }
        }
    }

    // Output the chosen action
    if (best_action == "CHECK") {
        cout << "ACTION CHECK" << endl;
    } else if (best_action == "FOLD") {
        cout << "ACTION FOLD" << endl;
    } else {
        cout << "ACTION RAISE " << best_x << endl;
    }
    cout.flush();
}

void process_result(const string& line) {
    // line starts with "RESULT"
    // We don't need to do anything except maybe record profit, but not required.
}

void process_opp(const string& line) {
    istringstream iss(line);
    string token, opp_action;
    iss >> token >> opp_action; // token is "OPP"
    if (opp_action == "FOLD") {
        // Next line must be RESULT
        string res_line;
        getline(cin, res_line);
        process_result(res_line);
    } else if (opp_action == "CALL") {
        int x;
        iss >> x;
        if (current_round == 4) {
            // Showdown, next line is RESULT
            string res_line;
            getline(cin, res_line);
            process_result(res_line);
        }
        // else, the next line will be a STATE, handled by main loop
    }
    // for "CHECK", nothing to do
}

void process_score(const string& line) {
    // Match finished, we could exit or ignore.
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    cin >> G;
    string dummy;
    getline(cin, dummy); // consume newline after G

    for (int hand = 1; hand <= G; ++hand) {
        while (true) {
            string line;
            getline(cin, line);
            if (line.empty()) continue;
            istringstream iss(line);
            string token;
            iss >> token;

            if (token == "-1") {
                return 0;
            } else if (token == "STATE") {
                process_state(line);
            } else if (token == "RESULT") {
                process_result(line);
                break; // hand finished
            } else if (token == "SCORE") {
                process_score(line);
                return 0;
            } else if (token == "OPP") {
                process_opp(line);
            } else {
                // Unknown token, but just ignore
            }
        }
    }
    return 0;
}