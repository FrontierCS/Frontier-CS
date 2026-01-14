#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>

void solve() {
    int n, m;
    std::cin >> n >> m;

    double beta = 1.0;
    if (m > 0) {
        // Theoretically motivated learning rate for the Hedge algorithm.
        // N = 2*n + 2 is the number of experts.
        beta = exp(-sqrt(2.0 * log(2.0 * n + 2.0) / m));
    }

    // w_A[i]: weight for the expert that mimics participant i.
    // w_B[i]: weight for the expert that predicts the opposite of participant i.
    std::vector<double> w_A(n, 1.0);
    std::vector<double> w_B(n, 1.0);
    // Weights for experts that always predict 0 or 1.
    double w_const0 = 1.0;
    double w_const1 = 1.0;

    for (int k = 0; k < m; ++k) {
        std::string s;
        std::cin >> s;

        // Tally weighted votes from all experts.
        double vote_0 = w_const0;
        double vote_1 = w_const1;

        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                vote_0 += w_A[i];
                vote_1 += w_B[i];
            } else {
                vote_1 += w_A[i];
                vote_0 += w_B[i];
            }
        }

        // Predict based on the majority vote, tie-breaking towards 1.
        int my_prediction = 0;
        if (vote_1 >= vote_0) {
            my_prediction = 1;
        }

        std::cout << my_prediction << std::endl;

        char outcome_char;
        std::cin >> outcome_char;
        int outcome = outcome_char - '0';

        // Update weights: penalize experts that were wrong.
        if (outcome == 0) {
            w_const1 *= beta;
        } else {
            w_const0 *= beta;
        }

        double max_w = std::max(w_const0, w_const1);

        for (int i = 0; i < n; ++i) {
            int p_i = s[i] - '0';
            if (p_i == outcome) { // Participant i was correct, so anti-expert B was wrong.
                w_B[i] *= beta;
            } else { // Participant i was wrong, so expert A was wrong.
                w_A[i] *= beta;
            }
            max_w = std::max({max_w, w_A[i], w_B[i]});
        }
        
        // Rescale weights to prevent floating-point underflow.
        if (max_w > 0 && max_w < 1e-100) {
            double scale_factor = 1e100;
            w_const0 *= scale_factor;
            w_const1 *= scale_factor;
            for (int i = 0; i < n; ++i) {
                w_A[i] *= scale_factor;
                w_B[i] *= scale_factor;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    solve();

    return 0;
}