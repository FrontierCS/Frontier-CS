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
#include <numeric>
using namespace std;

// Function to perform the swap operation on a permutation
void perform_operation(vector<int>& p, int x, int y) {
    int n = p.size();
    if (x <= 0 || y <= 0 || x + y >= n) {
        // This is an invalid operation, the checker will catch this.
        return;
    }
    vector<int> prefix(p.begin(), p.begin() + x);
    vector<int> middle(p.begin() + x, p.end() - y);
    vector<int> suffix(p.end() - y, p.end());
    p.clear();
    p.insert(p.end(), suffix.begin(), suffix.end());
    p.insert(p.end(), middle.begin(), middle.end());
    p.insert(p.end(), prefix.begin(), prefix.end());
}

bool check_sorted(vector <int> p) {
    for (int i = 0; i < p.size() - 1; i++) {
        if (p[i] > p[i + 1]) return false;
    }
    return true;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int n = inf.readInt();
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[i] = inf.readInt();
    }

    // int best_operations = ans.readInt();

    // Read contestant's output
    int m = ouf.readInt();
    if (m < 0 || m > 4 * n) {
        quitf(_wa, "Invalid number of operations m=%d. Must be between 0 and 4*n.", m);
    }

    vector<int> p_contestant = p;
    for (int i = 0; i < m; ++i) {
        int x = ouf.readInt();
        int y = ouf.readInt();
        if (x <= 0 || y <= 0 || x + y >= n) {
            quitf(_wa, "Invalid operation (x=%d, y=%d) for n=%d.", x, y, n);
        }
        perform_operation(p_contestant, x, y);
    }

    if (!check_sorted(p_contestant)) {
        quitf(_wa, "The final permutation is not the lexicographically smallest possible.");
    }

    // If we reach here, the permutation is correct. Now, calculate the score.
    int your_operations = m;
    int baseline_operations = 4 * n;
    int best_operations = 2 * n + 1;

    // 2*n+1 is a performance target, not a lower bound on required operations.
    // Legal shorter constructions must continue to receive higher scores.
    double performance = max(0.0, double(baseline_operations - your_operations)
                                  / (baseline_operations - best_operations));
    double ratio = 0.6 * performance;
    double unbounded_ratio = ratio;
    ratio = natural_log_score(100.0 * ratio, your_operations, best_operations, true) / 100.0;

    unbounded_ratio = ratio;
    quitp(ratio, "Final average score ratio. Ratio: %.12f, RatioUnbounded: %.12f", ratio, unbounded_ratio);
    return 0;
}
