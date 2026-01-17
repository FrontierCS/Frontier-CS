#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <cmath>
#include <iomanip>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // Parameters
    const double eta = 0.23;
    const double beta = exp(-eta); // approximately 0.794533

    // Initialize weights
    vector<double> w(n, 1.0);

    // Random number generator with fixed seed
    mt19937 rng(12345);
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int t = 0; t < m; ++t) {
        string s;
        cin >> s;

        // Compute total weight and weight for prediction 1
        double total = 0.0, total1 = 0.0;
        for (int i = 0; i < n; ++i) {
            double wi = w[i];
            total += wi;
            if (s[i] == '1') {
                total1 += wi;
            }
        }

        // Probability of predicting 1
        double p1 = total1 / total;

        // Random decision
        char prediction = (dist(rng) < p1) ? '1' : '0';
        cout << prediction << endl;
        cout.flush();

        // Read actual outcome
        char outcome_char;
        cin >> outcome_char;
        int outcome = outcome_char - '0';

        // Update weights: multiply by beta for wrong experts
        for (int i = 0; i < n; ++i) {
            if ((s[i] - '0') != outcome) {
                w[i] *= beta;
            }
        }

        // Renormalize weights if they become too small
        if (total < 1e-100) {
            for (int i = 0; i < n; ++i) {
                w[i] *= 1e100;
            }
        }
    }

    return 0;
}