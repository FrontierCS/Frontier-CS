#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <iomanip>

// Use a fixed seed for deterministic behavior of the randomized algorithm
std::mt19937 rng(42);

void solve() {
    int n;
    int m;
    std::cin >> n >> m;

    // Weights for the multiplicative weights update algorithm
    std::vector<long double> weights(n, 1.0L);
    // Keep track of mistakes for each participant to handle the b=0 case
    std::vector<int> mistakes(n, 0);

    for (int k = 0; k < m; ++k) {
        std::string s;
        std::cin >> s;

        int my_guess;

        // Find the minimum number of mistakes any participant has made so far.
        int min_mistakes = *std::min_element(mistakes.begin(), mistakes.end());

        // Hybrid Strategy:
        // If there is at least one "perfect" expert (0 mistakes so far), follow them.
        // This guarantees we make 0 mistakes if the best participant makes 0 mistakes (b=0).
        if (min_mistakes == 0) {
            int first_perfect_idx = -1;
            for (int i = 0; i < n; ++i) {
                if (mistakes[i] == 0) {
                    first_perfect_idx = i;
                    break;
                }
            }
            my_guess = s[first_perfect_idx] - '0';
        } else {
            // Otherwise, use Randomized Weighted Majority.
            long double weight_for_0 = 0.0L;
            long double weight_for_1 = 0.0L;

            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') {
                    weight_for_0 += weights[i];
                } else {
                    weight_for_1 += weights[i];
                }
            }

            long double total_weight = weight_for_0 + weight_for_1;
            
            // Handle the unlikely case where all weights decay to zero.
            if (total_weight == 0.0L) {
                my_guess = 0; // Default guess
            } else {
                long double prob_1 = weight_for_1 / total_weight;
                std::uniform_real_distribution<long double> dist(0.0L, 1.0L);
                if (dist(rng) < prob_1) {
                    my_guess = 1;
                } else {
                    my_guess = 0;
                }
            }
        }

        std::cout << my_guess << std::endl;

        int outcome;
        std::cin >> outcome;

        // Update mistakes and weights based on the actual outcome
        for (int i = 0; i < n; ++i) {
            if ((s[i] - '0') != outcome) {
                mistakes[i]++;
                // Penalize wrong experts by halving their weight.
                weights[i] *= 0.5L;
            }
        }
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    solve();

    return 0;
}