#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O operations for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    // Check for successful input reading
    if (cin >> n >> m) {
        // Weights for each participant, initialized to 1.0.
        // We use the Multiplicative Weights Update algorithm.
        vector<double> w(n, 1.0);
        
        // The penalty factor (beta).
        // A value in the range [0.8, 0.95] is typically effective for such problems.
        // It determines how quickly we discard experts who make mistakes.
        // beta = 0.9 provides a good balance between stability and adaptability.
        double beta = 0.9; 

        string s;
        // Reserve memory to avoid reallocations
        s.reserve(n);

        for (int t = 0; t < m; ++t) {
            cin >> s;
            
            double sum0 = 0.0;
            double sum1 = 0.0;
            
            // Calculate the weighted vote for '0' and '1'
            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') {
                    sum0 += w[i];
                } else {
                    sum1 += w[i];
                }
            }
            
            // Predict the outcome with the higher weighted sum
            int prediction = (sum1 > sum0) ? 1 : 0;
            cout << prediction << endl; // endl flushes the output, required for interaction
            
            int outcome;
            cin >> outcome;
            
            // Update weights based on the actual outcome
            // Reduce the weight of participants who guessed incorrectly
            for (int i = 0; i < n; ++i) {
                int guess = s[i] - '0';
                if (guess != outcome) {
                    w[i] *= beta;
                }
            }
            
            // Renormalize weights to prevent floating-point underflow
            // We track the maximum weight and scale up if it becomes too small.
            double max_w = 0.0;
            for (double val : w) {
                if (val > max_w) max_w = val;
            }
            
            // If the maximum weight is very small, multiply all weights by a large factor
            if (max_w < 1e-150) {
                for (int i = 0; i < n; ++i) {
                    w[i] *= 1e150;
                }
            }
        }
    }
    return 0;
}