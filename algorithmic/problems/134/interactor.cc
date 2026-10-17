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

// Calibrate a feasible performance reference to 60 percent.
static double referenceScore(double ratio) {
    return ratio <= 1.0 ? 0.6 * ratio : (0.6 + 0.02 * std::log(ratio));
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    // Read n from .in file
    long long n = inf.readLong();

    // Read secret information from .ans file
    long long ref_queries = ans.readLong();
    if (ref_queries < 0) quitf(_fail, "Reference queries must be nonnegative");
    long long hidden_a = ans.readLong();
    long long hidden_b = ans.readLong();

    // Validate hidden values
    if (hidden_a < 1 || hidden_a > n || hidden_b < 1 || hidden_b > n) {
        quitf(_fail, "Invalid hidden values in .ans file");
    }

    // Send n to contestant
    println(n);

    const int MAX_QUERIES = 10000;
    int query_count = 0;

    while (true) {
        query_count++;

        if (query_count > MAX_QUERIES) {
            quitp(0.0, "Query limit exceeded. Max queries: %d. Ratio: 0.0000", MAX_QUERIES);
        }

        long long x = ouf.readLong();
        long long y = ouf.readLong();

        // Validate query
        if (x < 1 || x > n || y < 1 || y > n) {
            quitf(_wa, "Invalid query: x and y must be in range [1, %lld]", n);
        }

        // Check if correct
        if (x == hidden_a && y == hidden_b) {
            println(0);

            // Preserve the original smoothed query normalization.
            double score_ratio = referenceScore(((double)ref_queries + 1.0) / ((double)query_count + 1.0));
    score_ratio = natural_log_score(100.0 * score_ratio, query_count, ref_queries, true) / 100.0;
            double unbounded_ratio = score_ratio;

            quitp(score_ratio, "Correct answer in %d queries. Ratio: %.12f, RatioUnbounded: %.12f", query_count, score_ratio, unbounded_ratio);
            break;
        }

        // Determine valid responses
        std::vector<int> valid_responses;

        if (x < hidden_a) {
            valid_responses.push_back(1);
        }
        if (y < hidden_b) {
            valid_responses.push_back(2);
        }
        if (x > hidden_a || y > hidden_b) {
            valid_responses.push_back(3);
        }

        // At least one response must be valid
        if (valid_responses.empty()) {
            // This shouldn't happen
            quitf(_fail, "Internal error: no valid response");
        }

        // Randomly choose one valid response
        int response = valid_responses[rnd.next(0, (int)valid_responses.size() - 1)];

        println(response);
    }

    return 0;
}
