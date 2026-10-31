#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"
#include <vector>
#include <string>


// Map normalized performance to the reference-anchored score, without a cap.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * std::log(r));
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    // Read n, l1, l2 from .in file (visible to contestant)
    int n = inf.readInt();
    int l1 = inf.readInt();  // Maximum allowed ask operations
    int l2 = inf.readInt();  // Maximum allowed swap operations

    // Read reference solution costs from .ans file
    int ref_s1 = ans.readInt();
    int ref_s2 = ans.readInt();
    ensuref(ref_s1 >= 0 && ref_s2 >= 0, "Reference operation counts must be nonnegative");

    // Read the hidden permutation from .in file
    std::vector<int> hidden_perm(n + 1);
    for (int i = 1; i <= n; ++i) {
        hidden_perm[i] = inf.readInt();
    }

    // Current state of the permutation (will be modified by swaps)
    std::vector<int> current_perm = hidden_perm;

    // Send n, l1, l2 to contestant
    println(n, l1, l2);

    int s1 = 0; // Count of ask operations
    int s2 = 0; // Count of swap operations

    // Helper function to count value-contiguous segments
    auto count_segments = [&](int l, int r) -> int {
        std::vector<bool> present(n + 1, false);
        int min_val = n + 1, max_val = 0;

        for (int i = l; i <= r; ++i) {
            present[current_perm[i]] = true;
            min_val = std::min(min_val, current_perm[i]);
            max_val = std::max(max_val, current_perm[i]);
        }

        // Count segments: a segment is a maximal contiguous range of present values
        int segments = 0;
        bool in_segment = false;
        for (int v = min_val; v <= max_val; ++v) {
            if (present[v]) {
                if (!in_segment) {
                    segments++;
                    in_segment = true;
                }
            } else {
                in_segment = false;
            }
        }
        return segments;
    };

    while (true) {
        int operation = ouf.readInt(1, 3);

        if (operation == 1) { // ask operation
            s1++;
            if (s1 > l1) {
                quitp(0.0, "Exceeded ask operation limit. Used %d, limit is %d. Ratio: 0.0000", s1, l1);
            }

            int l = ouf.readInt(1, n);
            int r = ouf.readInt(l, n);

            int result = count_segments(l, r);
            println(result);

        } else if (operation == 2) { // swp operation
            s2++;
            if (s2 > l2) {
                quitp(0.0, "Exceeded swap operation limit. Used %d, limit is %d. Ratio: 0.0000", s2, l2);
            }

            int i = ouf.readInt(1, n);
            int j = ouf.readInt(1, n);

            std::swap(current_perm[i], current_perm[j]);
            println(1);

        } else if (operation == 3) { // report operation
            std::vector<int> guess(n + 1);
            for (int i = 1; i <= n; ++i) {
                guess[i] = ouf.readInt(1, n);
            }

            // Check if it's a valid permutation
            std::vector<bool> seen(n + 1, false);
            bool valid = true;
            for (int i = 1; i <= n; ++i) {
                if (seen[guess[i]]) {
                    valid = false;
                    break;
                }
                seen[guess[i]] = true;
            }

            if (!valid) {
                quitp(0.0, "Invalid permutation in report. Ratio: 0.0000");
            }

            // Check if guess matches current_perm or its reverse
            bool matches_normal = true;
            bool matches_reverse = true;

            for (int i = 1; i <= n; ++i) {
                if (guess[i] != current_perm[i]) {
                    matches_normal = false;
                }
                if (guess[i] != (n - current_perm[i] + 1)) {
                    matches_reverse = false;
                }
            }

            if (!matches_normal && !matches_reverse) {
                quitp(0.0, "Wrong answer. s1=%d, s2=%d. Ratio: 0.0000", s1, s2);
            }

            // Calculate score
            double normalized_performance = ((double)ref_s1 + ref_s2 + 1.0) / ((double)s1 + s2 + 1.0);
            double score_ratio = referenceScore(normalized_performance);
    score_ratio = natural_log_score(100.0 * score_ratio, (long double)s1+s2, (long double)ref_s1+ref_s2, true) / 100.0;
            double unbounded_ratio = score_ratio;

            quitp(score_ratio, "Correct answer. s1=%d, s2=%d. Ratio: %.12f, RatioUnbounded: %.12f", s1, s2, score_ratio, unbounded_ratio);

        }
    }

    return 0;
}
