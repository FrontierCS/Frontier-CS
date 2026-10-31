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

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    int n = inf.readInt();
    long long ref_queries = ans.readLong();
    ensuref(ref_queries > 0, "Reference query count must be positive");
    std::vector<int> hidden_permutation(n + 1);
    for (int i = 1; i <= n; ++i) {
        hidden_permutation[i] = inf.readInt();
    }

    println(n);

    const int MAX_QUERIES = 500;
    int query_count = 0;

    while (true) {
        int action_type = ouf.readInt(); // 0 for query, 1 for answer

        if (action_type == 0) { // Query
            if (++query_count > MAX_QUERIES) {
                quitp(0.0, "Query limit exceeded. Max queries: %d. Ratio: 0.0000", MAX_QUERIES);
            }

            int k = ouf.readInt();

            if (k < 4 || k > n || k % 2 != 0) {
                quitf(_wa, "Invalid k: %d", k);
            }

            std::vector<int> indices(k);
            std::vector<bool> used(n + 1, false);

            for (int i = 0; i < k; ++i) {
                indices[i] = ouf.readInt();
                if (indices[i] < 1 || indices[i] > n || used[indices[i]]) {
                    quitf(_wa, "Invalid query indices");
                }
                used[indices[i]] = true;
            }

            std::vector<int> values(k);
            for (int i = 0; i < k; ++i) {
                values[i] = hidden_permutation[indices[i]];
            }

            std::sort(values.begin(), values.end());

            int median1 = values[k / 2 - 1];
            int median2 = values[k / 2];

            println(median1, median2);

        } else if (action_type == 1) { // Final answer
            int i1 = ouf.readInt();
            int i2 = ouf.readInt();

            if (i1 < 1 || i1 > n || i2 < 1 || i2 > n) {
                quitf(_wa, "Invalid answer indices");
            }

            int target1 = n / 2;
            int target2 = n / 2 + 1;

            int val1 = hidden_permutation[i1];
            int val2 = hidden_permutation[i2];

            bool correct = (val1 == target1 && val2 == target2) ||
                          (val1 == target2 && val2 == target1);

            if (correct) {
                // A one-query shift keeps valid zero-query guesses finite.
                // This intentionally changes the old inverse-query normalization.
                double performance = (static_cast<double>(ref_queries) + 1.0) / (query_count + 1.0);
                double score_ratio = performance <= 1.0
                    ? 0.6 * performance
                    : (0.6 + 0.02 * std::log(performance));
    score_ratio = natural_log_score(100.0 * score_ratio, query_count, ref_queries, true) / 100.0;
                double unbounded_ratio = score_ratio;
                quitp(score_ratio, "Correct in %d queries. Ratio: %.12f, RatioUnbounded: %.12f", query_count, score_ratio, unbounded_ratio);
            } else {
                quitp(0.0, "Wrong answer. Ratio: 0.0000, RatioUnbounded: 0.0000");
            }
            break;

        } else {
            quitf(_wa, "Invalid action type: %d", action_type);
        }
    }

    return 0;
}
