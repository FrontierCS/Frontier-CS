#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <limits>

// Use long double for better precision to avoid underflow with small weights.
using LD = long double;

// Calculates log(sum(exp(v_i))) for a vector of log-values v_i.
// This is a numerically stable way to compute the logarithm of a sum of exponentials.
LD log_sum_exp(const std::vector<LD>& logs) {
    if (logs.empty()) {
        // The sum over an empty set is 0. log(0) is -infinity.
        return -std::numeric_limits<LD>::infinity();
    }

    LD max_val = *std::max_element(logs.begin(), logs.end());

    LD sum_exp = 0.0;
    for (LD val : logs) {
        sum_exp += expl(val - max_val);
    }
    
    return max_val + logl(sum_exp);
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n; // Number of other participants
    int m; // Number of wagers
    std::cin >> n >> m;

    std::vector<LD> log_weights(n, 0.0); // Initially, all log-weights are log(1) = 0.

    const LD eta = 0.5;
    const LD log_eta = logl(eta);

    for (int k = 0; k < m; ++k) {
        std::string predictions;
        std::cin >> predictions;

        // Separate experts based on their prediction ('0' or '1').
        std::vector<LD> group0_logs;
        std::vector<LD> group1_logs;
        for (int i = 0; i < n; ++i) {
            if (predictions[i] == '0') {
                group0_logs.push_back(log_weights[i]);
            } else {
                group1_logs.push_back(log_weights[i]);
            }
        }

        // Calculate the total weighted "vote" for '0' and '1' in log-space.
        LD log_w0 = log_sum_exp(group0_logs);
        LD log_w1 = log_sum_exp(group1_logs);

        // Predict based on which group has a higher total weight.
        // Tie-break goes to '0'.
        char my_prediction;
        if (log_w0 >= log_w1) {
            my_prediction = '0';
        } else {
            my_prediction = '1';
        }

        // Output our prediction. `std::endl` also flushes the stream.
        std::cout << my_prediction << std::endl;

        // Read the actual outcome of the wager.
        char outcome;
        std::cin >> outcome;

        // Update the weights. Penalize experts who were wrong.
        // In log-space, multiplying by eta becomes adding log(eta).
        for (int i = 0; i < n; ++i) {
            if (predictions[i] != outcome) {
                log_weights[i] += log_eta;
            }
        }
    }

    return 0;
}