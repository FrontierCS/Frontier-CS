#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include "testlib.h"
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <cctype>
#include <climits>

using namespace std;

// Apply operation: choose indices (i, j) with 1 <= i < j <= n
// Replace A_i with A_j - 1 and A_j with A_i + 1
void apply_op(vector<int>& a, int i, int j) {
    int u = i - 1;  // Convert to 0-based index
    int v = j - 1;  // Convert to 0-based index
    int old_ai = a[u];
    int old_aj = a[v];
    a[u] = old_aj - 1;
    a[v] = old_ai + 1;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    int n = inf.readInt();
    vector<int> initial_a = inf.readInts(n);
    vector<int> target_b = inf.readInts(n);

    // Read user and standard output: first token should be "Yes" or "No"
    string user_token = ouf.readToken();
    string std_token = ans.readToken();

    // Convert to uppercase for case-insensitive comparison
    string user_upper = user_token;
    string std_upper = std_token;
    for (char &c : user_upper) c = toupper(c);
    for (char &c : std_upper) c = toupper(c);

    // Validate user output format
    if (user_upper != "YES" && user_upper != "NO") {
        double score_ratio = 0.0;
        double unbounded_ratio = 0.0;
        quitp(score_ratio, "Value: 0. Ratio: %.12f, RatioUnbounded: %.12f. Output must start with 'Yes' or 'No', found '%s'",
              score_ratio, unbounded_ratio, user_token.c_str());
    }

    bool user_possible = (user_upper == "YES");
    bool std_possible = (std_upper == "YES");

    // Check if user's answer matches standard answer
    if (!user_possible && std_possible) {
        double score_ratio = 0.0;
        double unbounded_ratio = 0.0;
        quitp(score_ratio, "Value: 0. Ratio: %.12f, RatioUnbounded: %.12f. Participant found no solution, but solution exists.",
              score_ratio, unbounded_ratio);
    }

    if (user_possible && !std_possible) {
        double score_ratio = 0.0;
        double unbounded_ratio = 0.0;
        quitp(score_ratio, "Value: 0. Ratio: %.12f, RatioUnbounded: %.12f. Participant claims 'Yes' but standard answer is 'No'.",
              score_ratio, unbounded_ratio);
    }

    // If both say "No", it's correct
    if (!user_possible && !std_possible) {
        double score_ratio = 1.0;
        double unbounded_ratio = 1.0;
        quitp(score_ratio, "Value: 0. Ratio: %.12f, RatioUnbounded: %.12f. Correct result: No solution.",
              score_ratio, unbounded_ratio);
    }

    // Both say "Yes", now check the operation sequence
    int m_std = ans.readInt();  // Standard answer: number of operations
    int m_user = ouf.readInt(0, INT_MAX, "operation count");  // Nonnegative number of operations

    vector<int> current_a = initial_a;

    // Simulate user's operations
    for (int k = 0; k < m_user; k++) {
        int i = ouf.readInt();
        int j = ouf.readInt();

        // Validate operation indices
        if (i < 1 || i > n || j < 1 || j > n) {
            double score_ratio = 0.0;
            double unbounded_ratio = 0.0;
            quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f. Operation %d: indices (%d, %d) out of bounds [1, %d]",
                  m_user, score_ratio, unbounded_ratio, k + 1, i, j, n);
        }

        if (i >= j) {
            double score_ratio = 0.0;
            double unbounded_ratio = 0.0;
            quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f. Operation %d: indices (%d, %d) do not satisfy i < j",
                  m_user, score_ratio, unbounded_ratio, k + 1, i, j);
        }

        apply_op(current_a, i, j);
    }

    // Check if final sequence matches target
    if (current_a != target_b) {
        double score_ratio = 0.0;
        double unbounded_ratio = 0.0;
        quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f. Final sequence does not match target B.",
              m_user, score_ratio, unbounded_ratio);
    }

    // A zero-operation standard answer is an exact theoretical optimum.
    // Otherwise, the standard operation count is a performance reference.
    double score_ratio;
    if (m_std == 0) {
        score_ratio = (m_user <= 0) ? 1.0 : 0.0;
    } else {
        if (m_std < 0) quitf(_fail, "Negative reference operation count");
        double performance = max(0.0, (2.0 * m_std - m_user) / m_std);
        score_ratio = (0.6 * performance);
    }
    score_ratio = natural_log_score(100.0L * (score_ratio), m_user, m_std, true) / 100.0;
    double unbounded_ratio = score_ratio;

    // Use standard quitp format
    quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f", m_user, score_ratio, unbounded_ratio);

    return 0;
}
