#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <random>
#include <algorithm>

using namespace std;

// The Strategy struct represents an expert algorithm (Randomized Weighted Majority)
// running with a specific learning rate (epsilon).
struct Strategy {
    int n;
    double epsilon;
    vector<double> log_weights;

    Strategy(int n, double eps) : n(n), epsilon(eps), log_weights(n, 0.0) {}

    // Calculate the probability of the outcome being 1 based on current weights
    double get_probability(const string& predictions) {
        double max_lw = -1e18;
        for (double lw : log_weights) {
            if (lw > max_lw) max_lw = lw;
        }

        double sum0 = 0.0;
        double sum1 = 0.0;

        for (int i = 0; i < n; ++i) {
            // Compute exp(weight - max_weight) to avoid overflow/underflow
            double w = exp(log_weights[i] - max_lw);
            if (predictions[i] == '0') sum0 += w;
            else sum1 += w;
        }

        if (sum0 + sum1 < 1e-100) return 0.5; // Should ideally not happen
        return sum1 / (sum0 + sum1);
    }

    // Update weights based on the actual outcome
    void update(const string& predictions, int outcome) {
        // Multiplicative Weights Update: w_i = w_i * (1 - epsilon) if mistake
        // In log space: log(w_i) = log(w_i) + log(1 - epsilon)
        double log_penalty = log(1.0 - epsilon);
        for (int i = 0; i < n; ++i) {
            int p = predictions[i] - '0';
            if (p != outcome) {
                log_weights[i] += log_penalty;
            }
        }
    }
};

int main() {
    // Optimize standard I/O for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // We do not know the best learning rate beforehand (it depends on the best participant's error rate).
    // So we use a "Meta" strategy that aggregates multiple expert strategies with different epsilons.
    vector<double> epsilons = {0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5};
    vector<Strategy> strategies;
    for (double eps : epsilons) {
        strategies.emplace_back(n, eps);
    }

    int k = strategies.size();
    vector<double> meta_weights(k, 1.0);
    // Meta learning rate for the aggregation level
    double meta_eta = 0.1;

    // Random number generator for randomized decisions
    mt19937 rng(1337);
    uniform_real_distribution<double> dist(0.0, 1.0);

    for (int round = 0; round < m; ++round) {
        string preds;
        cin >> preds;

        // Get probabilities from all sub-strategies and aggregate them
        vector<double> strat_probs(k);
        double weighted_prob_sum = 0.0;
        double meta_weight_sum = 0.0;

        for (int i = 0; i < k; ++i) {
            strat_probs[i] = strategies[i].get_probability(preds);
            weighted_prob_sum += meta_weights[i] * strat_probs[i];
            meta_weight_sum += meta_weights[i];
        }

        double final_prob_1 = (meta_weight_sum > 1e-100) ? (weighted_prob_sum / meta_weight_sum) : 0.5;
        
        // Output prediction based on the aggregated probability.
        // Randomized choice is essential for the regret bounds of Multiplicative Weights.
        int my_guess = (dist(rng) < final_prob_1) ? 1 : 0;
        cout << my_guess << endl;

        // Read actual outcome
        int actual;
        cin >> actual;

        // Update sub-strategies based on their performance
        for (int i = 0; i < k; ++i) {
            strategies[i].update(preds, actual);
        }

        // Update meta-weights based on the performance (loss) of each strategy
        // Using absolute loss |prob - actual|
        for (int i = 0; i < k; ++i) {
            double loss = abs(strat_probs[i] - (double)actual);
            meta_weights[i] *= exp(-meta_eta * loss);
        }

        // Normalize meta-weights to prevent floating point underflow
        double max_w = 0.0;
        for(double w : meta_weights) max_w = max(max_w, w);
        if (max_w < 1e-200) {
            for(double &w : meta_weights) w *= 1e200;
        }
    }

    return 0;
}