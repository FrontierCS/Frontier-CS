#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>

using namespace std;

int main() {
    // Use fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    // Check for input success to handle potential empty input or errors
    if (!(cin >> n >> m)) return 0;

    // Weights for each participant, initialized to 1.0
    vector<double> w(n, 1.0);

    // Learning rate eta
    // Theoretical optimal for MWU is roughly sqrt(ln(N)/M).
    // For N=1000, M=10000, sqrt(ln(1000)/10000) approx 0.026.
    // We choose 0.05 to adapt reasonably quickly while maintaining stability.
    double eta = 0.05;

    // Setup random number generator
    // Use steady_clock to ensure a changing seed if the program is run multiple times
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int t = 0; t < m; ++t) {
        string s;
        cin >> s;

        double w0 = 0.0;
        double w1 = 0.0;

        // Accumulate weights for each prediction (0 or 1)
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') {
                w0 += w[i];
            } else {
                w1 += w[i];
            }
        }

        // Determine Izzy's guess using Randomized Weighted Majority
        int my_guess = 0;
        double sum_w = w0 + w1;

        if (sum_w < 1e-200) {
            // If weights underflow significantly (should be handled by rescaling, but as a safeguard)
            my_guess = (dist(rng) < 0.5) ? 0 : 1;
        } else {
            // Probability of predicting 1 is proportional to the total weight of participants predicting 1
            double prob1 = w1 / sum_w;
            if (dist(rng) < prob1) {
                my_guess = 1;
            } else {
                my_guess = 0;
            }
        }

        // Output prediction and flush
        cout << my_guess << endl;

        // Read actual outcome
        int outcome;
        cin >> outcome;

        // Update weights: penalize participants who made a mistake
        double max_w = 0.0;
        for (int i = 0; i < n; ++i) {
            int pred = s[i] - '0';
            if (pred != outcome) {
                w[i] *= (1.0 - eta);
            }
            if (w[i] > max_w) max_w = w[i];
        }

        // Rescale weights to prevent underflow if the maximum weight drops too low
        if (max_w < 1e-150) {
            double scale = 1e150;
            for (int i = 0; i < n; ++i) {
                w[i] *= scale;
            }
        }
    }

    return 0;
}