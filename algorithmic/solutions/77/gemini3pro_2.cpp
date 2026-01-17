#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for performance
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    // Read number of participants (n) and wagers (m)
    if (cin >> n >> m) {
        // Initialize weights for each participant to 1.0
        // We use the Multiplicative Weights Update algorithm.
        vector<double> w(n, 1.0);
        
        // Beta is the penalty factor applied to weights of participants who predict incorrectly.
        // A value of 0.8 allows the algorithm to quickly converge to the best performing experts,
        // which is crucial to minimize the number of mistakes relative to the best expert (b).
        double beta = 0.8; 

        for (int k = 0; k < m; ++k) {
            string s;
            cin >> s;
            
            // Calculate weighted votes for '0' and '1'
            double v0 = 0.0;
            double v1 = 0.0;
            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') {
                    v0 += w[i];
                } else {
                    v1 += w[i];
                }
            }

            // Make prediction based on the weighted majority
            char guess = (v1 > v0) ? '1' : '0';
            cout << guess << endl; // Use endl to ensure output is flushed

            // Read the actual outcome of the wager
            char outcome;
            cin >> outcome;
            
            // Update weights based on the outcome
            double max_w = 0.0;
            for (int i = 0; i < n; ++i) {
                if (s[i] != outcome) {
                    w[i] *= beta;
                }
                if (w[i] > max_w) {
                    max_w = w[i];
                }
            }
            
            // Renormalize weights to prevent floating point underflow
            // if the maximum weight becomes extremely small.
            if (max_w < 1e-150) {
                for (int i = 0; i < n; ++i) {
                    w[i] *= 1e150;
                }
            }
        }
    }

    return 0;
}