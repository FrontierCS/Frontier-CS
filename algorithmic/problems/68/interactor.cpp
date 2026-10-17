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


// Preserve the bounded base ratio for the unchanged low-score branch.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>

int main(int argc, char* argv[]) {
	registerInteraction(argc, argv);

	int t = inf.readInt();
	println(t);

	int cnt = 0;
	for (int tt = 0; tt < t; tt++) {
		int n = inf.readInt();
		println(n);

		std::vector<int> a(n);
		for (int i = 0; i < n; i++) {
			a[i] = inf.readInt();
		}

		while (true) {
			int op = ouf.readInt();
			if (op == 0) {
				int i = ouf.readInt();
				if (i < 0 || i >= n) {
					quitf(_wa, "Invalid query: element %d is out of range [0, %d]", i, n - 1);
				}

				if (a[i]) {
					a[i]--;
					println(1);
				} else {
					println(0);
				}
			} else if (op == 1) {
				int i = ouf.readInt();
				if (i < 0 || i >= n) {
					quitf(_wa, "Invalid query: element %d is out of range [0, %d]", i, n - 1);
				}
				int j = ouf.readInt();
				if (j < 0 || j >= n) {
					quitf(_wa, "Invalid query: element %d is out of range [0, %d]", j, n - 1);
				}
				if (i == j) {
					quitf(_wa, "%d and %d can not be equal.", i, j);
				}

				cnt += a[i] + a[j] >= n;
				break;
			} else {
				quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", op);
			}
		}
	}

	double ratio = 1. * cnt / t;
	ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, cnt, 0.6L*t, false) / 100.0;
	quitp(ratio, "Ratio: %.12f", ratio);

	return 0;
}
