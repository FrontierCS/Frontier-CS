#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <random>
#include <algorithm>

using namespace std;

int main() {
    // Use fast I/O, but careful with flushing.
    // cin and cout are tied by default, and endl flushes.
    // We keep sync_with_stdio(false) for performance given the loop size.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    // Reading n and m
    if (!(cin >> n >> m)) return 0;

    // Weights for the experts (other participants)
    // Initially all weights are 1.0
    vector<double> w(n, 1.0);

    // Calculate learning rate eta
    // The theoretical optimal eta for Multiplicative Weights Update (MWU) is approx sqrt(ln(N)/M).
    // We use a heuristic factor to tune performance.
    double eta = 0.0;
    if (m > 0) {
        // sqrt(4 * ln(n) / m) is a reasonable heuristic
        eta = sqrt(log(n) * 4.0 / m);
    }
    
    // Clamp eta to ensure stability
    // An eta too large causes oscillation, too small causes slow learning.
    if (eta > 0.5) eta = 0.5;
    if (eta < 0.01) eta = 0.01;

    // Random number generator with a fixed seed for reproducibility.
    // The problem states inputs are deterministic/fixed per test case.
    mt19937 rng(1337);
    uniform_real_distribution<double> dist(0.0, 1.0);

    string s;
    s.reserve(n);

    for (int k = 0; k < m; ++k) {
        // Read participants' predictions
        cin >> s;
        
        double w0 = 0.0;
        double w1 = 0.0;
        
        // Sum weights for 0 and 1
        for (int i = 0; i < n; ++i) {
            if (s[i] == '0') w0 += w[i];
            else w1 += w[i];
        }

        // Calculate probability to predict 1 based on weighted majority
        double p1 = 0.0;
        double total_w = w0 + w1;
        if (total_w > 0) {
            p1 = w1 / total_w;
        } else {
            p1 = 0.5; // Fallback if weights underflow significantly (handled by rescaling below)
        }

        // Make a prediction using the calculated probability
        // Randomized strategy helps minimize worst-case regret
        int prediction = (dist(rng) < p1) ? 1 : 0;
        
        // Print prediction and flush
        cout << prediction << endl;

        // Read actual outcome
        int actual;
        cin >> actual;

        // Update weights based on the outcome
        // Experts who predicted incorrectly are penalized
        char actual_char = actual + '0';
        double penalty = 1.0 - eta;
        double max_w = 0.0;

        for (int i = 0; i < n; ++i) {
            if (s[i] != actual_char) {
                w[i] *= penalty;
            }
            if (w[i] > max_w) {
                max_w = w[i];
            }
        }

        // Rescale weights to prevent floating point underflow
        // If the maximum weight drops too low, multiply all by a large constant
        if (max_w < 1e-150) {
            double scale = 1e150;
            for (int i = 0; i < n; ++i) {
                w[i] *= scale;
            }
        }
    }

    return 0;
}