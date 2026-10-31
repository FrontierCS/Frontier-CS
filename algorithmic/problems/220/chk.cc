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
#include <cmath>
#include <algorithm>
// Historical calibration; the physical-objective mapping is applied below.
static double reference_score(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6*r : 0.6 + 0.02*std::log(r);
}

#include <iostream>
#include <algorithm>
#include <cstdio>

using namespace std;

const int N = 521;
int n, c[N][N], a[N];

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input: n players, each has n cards
    n = inf.readInt();
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            int x = inf.readInt();
            if (x < 1 || x > n) {
                quitf(_fail, "Invalid input: card number %d out of range [1, %d]", x, n);
            }
            ++c[i][x];
        }
    }

    // Read output: number of operations
    int cnt = ouf.readInt();
    if (cnt < 0 || cnt > n * n * 2) {
        quitf(_wa, "Operation number out of range: %d (expected 0 to %d)", cnt, n * n * 2);
    }
    int num = cnt;

    // Simulate operations
    while (cnt--) {
        // Read one operation: n cards to pass
        for (int i = 1; i <= n; i++) {
            a[i] = ouf.readInt();
            if (a[i] < 1 || a[i] > n) {
                quitf(_wa, "Card number out of range: %d (expected 1 to %d)", a[i], n);
            }
            if (!c[i][a[i]]) {
                quitf(_wa, "Player %d does not have card %d to pass", i, a[i]);
            }
            --c[i][a[i]];
        }
        // Pass cards to the right (player i passes to player (i % n) + 1)
        for (int i = 1; i <= n; i++) {
            ++c[i % n + 1][a[i]];
        }
    }

    // Verify final state: each player i should have exactly n cards with number i
    for (int i = 1; i <= n; i++) {
        if (c[i][i] != n) {
            quitf(_wa, "Player %d does not have exactly %d cards with number %d (has %d)", i, n, i, c[i][i]);
        }
    }

    // Calculate score based on number of operations
    // According to the problem solution:
    // - Optimal solution: at most n*(n-1)/2 operations for each part = n*n - n total
    // - Perfect score threshold: n*n/2 (half of maximum)
    // - Maximum acceptable: n*n - n
    double base_score = n * n - n;  // Maximum operations from solution
    double perfect = n * n / 2.0;   // Perfect score threshold

    double performance = base_score > perfect
        ? max(0.0, (base_score-num)/(base_score-perfect))
        : (perfect+1.0)/(num+1.0);
    double score_ratio = reference_score(performance);
    score_ratio = natural_log_score(100.0L * (score_ratio), num, perfect, true) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Value: %d. Ratio: %.12f, RatioUnbounded: %.12f", num, score_ratio, unbounded_ratio);

    return 0;
}
