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

	int n = inf.readInt();
	println(n);

	std::vector<int> a(n);
	for (int i = 0; i < n; i++) {
		a[i] = inf.readInt();
	}

	std::vector s(n + 1, std::vector(n + 1, false));
	for (int i = 0; i < n; i++) {
		for (int j = i + 1; j < n; j++) {
			s[i + 1][j + 1] = a[i] > a[j];
		}
	}
	for (int i = 0; i < n; i++) {
		for (int j = 0; j <= n; j++) {
			s[i + 1][j] = s[i + 1][j] ^ s[i][j];
		}
	}
	for (int i = 0; i <= n; i++) {
		for (int j = 0; j < n; j++) {
			s[i][j + 1] = s[i][j + 1] ^ s[i][j];
		}
	}

	for (int q = 0; q <= 1999000; q++) {
		int op = ouf.readInt();
		if (op == 0) {
			int l = ouf.readInt();
			if (l < 1 || l > n) {
				quitf(_wa, "Invalid query: element %d is out of range [1, %d]", l, n);
			}
			int r = ouf.readInt();
			if (r < 1 || r > n) {
				quitf(_wa, "Invalid query: element %d is out of range [1, %d]", r, n);
			}
			if (l > r) {
				quitf(_wa, "Invalid query: not an interval.");
			}
			l--;

			println(s[r][r] ^ s[l][r] ^ s[r][l] ^ s[l][l]);
		} else if (op == 1) {
			std::vector<int> b(n);
			for (int i = 0; i < n; i++) {
				b[i] = ouf.readInt();
			}
			if (b == a) {
				double ratio = (std::exp(1. * -q / 249875) - std::exp(-8)) / (1 - std::exp(-8));
				ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, q, -249875.0L*std::log(0.6L+0.4L*std::exp(-8.0L)), true) / 100.0;
				quitp(ratio, "Correct guess. Ratio: %.12f", ratio);
			} else {
				quitp(0., "Wrong guess. Ratio: 0.0000");
			}
		} else {
			quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", op);
		}
	}
	quitp(0., "Too many queries. Ratio: 0.0000");

	return 0;
}
