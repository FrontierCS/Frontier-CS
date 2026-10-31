#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}

#include "testlib.h"
#include <vector>
#include <deque>
#include <set>
#include <string>


// Map normalized performance to the reference-anchored score, without a cap.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * std::log(r));
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int n = inf.readInt();
    int k = inf.readInt();

    std::vector<int> hidden_array(n + 1);
    for (int i = 1; i <= n; ++i) {
        hidden_array[i] = inf.readInt();
    }

    long long ref_cost = ans.readLong();
    ensuref(ref_cost > 0, "Reference cost must be positive");

    println(n, k);

    const int MAX_OPERATIONS = 100000;
    int query_count = 0;
    int reset_count = 0;

    std::deque<int> S; // Memory queue

    while (true) {
        std::string operation = ouf.readToken();

        if (operation == "?") { // Query
            query_count++;

            if (query_count + reset_count > MAX_OPERATIONS) {
                quitp(0.0, "Operation limit exceeded. Max operations: %d. Ratio: 0.0000", MAX_OPERATIONS);
            }

            int c = ouf.readInt();

            if (c < 1 || c > n) {
                quitf(_wa, "Invalid query: bakery index must be between 1 and %d", n);
            }

            int cake_type = hidden_array[c];

            // Check if cake_type is in S
            bool found = false;
            for (int val : S) {
                if (val == cake_type) {
                    found = true;
                    break;
                }
            }

            // Output Y or N
            if (found) {
                println("Y");
            } else {
                println("N");
            }

            // Add cake_type to the end of S
            S.push_back(cake_type);

            // If |S| > k, remove front
            if ((int)S.size() > k) {
                S.pop_front();
            }

        } else if (operation == "R") { // Reset
            reset_count++;

            if (query_count + reset_count > MAX_OPERATIONS) {
                quitp(0.0, "Operation limit exceeded. Max operations: %d. Ratio: 0.0000", MAX_OPERATIONS);
            }

            // Clear S (no response to contestant)
            S.clear();

        } else if (operation == "!") { // Final answer
            int d = ouf.readInt();

            if (d < 1 || d > n) {
                quitf(_wa, "Invalid answer: d must be between 1 and %d", n);
            }

            // Calculate the actual number of distinct values
            std::set<int> distinct_values;
            for (int i = 1; i <= n; ++i) {
                distinct_values.insert(hidden_array[i]);
            }
            int actual_d = distinct_values.size();

            if (d != actual_d) {
                quitp(0.0, "Wrong answer: expected %d, got %d. Ratio: 0.0000", actual_d, d);
            }

            // Calculate cost
            long long your_cost = (long long)reset_count * n + query_count + 1;

            double normalized_performance = (double)ref_cost / your_cost;
            double score_ratio = referenceScore(normalized_performance);
    score_ratio = natural_log_score(100.0 * score_ratio, your_cost, ref_cost, true) / 100.0;
            double unbounded_ratio = score_ratio;
            quitp(score_ratio, "Correct in %d queries and %d resets. Cost: %lld. Ratio: %.12f, RatioUnbounded: %.12f",
                  query_count, reset_count, your_cost, score_ratio, unbounded_ratio);
            break;

        } else {
            quitf(_wa, "Invalid operation: expected '?', 'R', or '!', but got '%s'", operation.c_str());
        }
    }

    return 0;
}
