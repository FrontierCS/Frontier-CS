#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // Initialize weights for each participant
    vector<double> weights(n, 1.0);
    const double beta = 0.6;  // multiplicative update factor for wrong experts

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int round = 0; round < m; ++round) {
        string predictions;
        cin >> predictions;

        // Compute total weight for prediction 0 and 1
        double weight0 = 0.0, weight1 = 0.0;
        for (int i = 0; i < n; ++i) {
            if (predictions[i] == '0')
                weight0 += weights[i];
            else
                weight1 += weights[i];
        }

        // Probability of predicting 1
        double prob1 = weight1 / (weight0 + weight1);
        double u = dist(rng);
        char my_prediction = (u < prob1) ? '1' : '0';

        cout << my_prediction << endl;
        cout.flush();

        char actual;
        cin >> actual;

        // Update weights: shrink weights of wrong experts
        double new_total = 0.0;
        for (int i = 0; i < n; ++i) {
            if (predictions[i] != actual) {
                weights[i] *= beta;
            }
            new_total += weights[i];
        }

        // Renormalize weights to avoid numerical issues
        for (int i = 0; i < n; ++i) {
            weights[i] /= new_total;
        }
    }

    return 0;
}