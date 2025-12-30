#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

void solve() {
    // Fast I/O for interactive problems
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n; // Number of other participants
    int m; // Number of wagers
    std::cin >> n >> m;

    // Weights for "expert" i (predicts same as participant i)
    std::vector<long double> w_E(n, 1.0L);
    // Weights for "anti-expert" i (predicts opposite of participant i)
    std::vector<long double> w_A(n, 1.0L);

    // Multiplicative weight update parameter.
    // Based on theoretical bounds for this type of problem and the likely scoring function,
    // a value of 0.85 is a robust choice.
    const long double beta = 0.85L;

    // Loop through all m wagers
    for (int k = 0; k < m; ++k) {
        // Read predictions of other participants
        std::string s;
        std::cin >> s;

        long double vote_0 = 0.0L;
        long double vote_1 = 0.0L;

        // Calculate weighted votes for 0 and 1 from all 2n meta-experts
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                vote_0 += w_E[i];
                vote_1 += w_A[i];
            } else { // s[i] == '1'
                vote_1 += w_E[i];
                vote_0 += w_A[i];
            }
        }
        
        // Make prediction. A consistent tie-breaking rule is chosen (predict '1').
        char my_prediction;
        if (vote_1 >= vote_0) {
            my_prediction = '1';
        } else {
            my_prediction = '0';
        }
        
        // Output prediction and flush the stream, as required by the interactive protocol.
        std::cout << my_prediction << std::endl;

        // Read the actual outcome
        char outcome;
        std::cin >> outcome;

        // Update weights based on the outcome
        for (int i = 0; i < n; ++i) {
            if (s[i] == outcome) { // participant i was correct
                // Their "expert" was right, "anti-expert" was wrong
                w_A[i] *= beta;
            } else { // participant i was incorrect
                // Their "expert" was wrong, "anti-expert" was right
                w_E[i] *= beta;
            }
        }
        
        // Normalization step to prevent weights from underflowing to zero.
        // Find the maximum weight among all 2n meta-experts.
        long double max_w = 0.0L;
        for (int i = 0; i < n; ++i) {
            if (w_E[i] > max_w) max_w = w_E[i];
            if (w_A[i] > max_w) max_w = w_A[i];
        }
        
        // If max_w is positive and has become very small, rescale all weights.
        // This keeps the relative weights the same but in a healthier numerical range.
        if (max_w > 0 && max_w < 1e-50L) {
            long double inv_max_w = 1.0L / max_w;
            for (int i = 0; i < n; ++i) {
                w_E[i] *= inv_max_w;
                w_A[i] *= inv_max_w;
            }
        }
    }
}

int main() {
    solve();
    return 0;
}