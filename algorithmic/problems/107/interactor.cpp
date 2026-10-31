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


// Legacy base ratio, retained only to decide and preserve the lower band.
static double penalized(double s) {
    return std::max(0.0, std::min(1.0, s));
}

#include "testlib.h"
#include <bits/stdc++.h>

using i64 = long long;

int main(int argc, char* argv[]) {
	registerInteraction(argc, argv);

	int t = inf.readInt();
	println(t);

	int max = 0;
	while (t--) {
		int x = inf.readInt();
		for (int q = 0; q <= 100; q++) {
			if (q == 100) {
				quitp(0., "Too many queries. Ratio: 0.0000");
			}

			int op = ouf.readInt();
			if (op == 0) {
				i64 y = ouf.readLong();
				if (y < 1 || y > 1000000000000000000) {
					quitf(_wa, "Invalid query: element %lld is out of range [1, 1000000000000000000]", y);
				}

				println(std::gcd(x, y));
			} else if (op == 1) {
				// The guess may be any int, so 2 * d and a - d need 64 bits.
				i64 a = ans.readInt(), d = ouf.readInt();
				if (std::abs(a - d) <= 7 || (2 * a >= d && 2 * d >= a)) {
					max = std::max(max, q);
					break;
				} else {
					quitp(0., "Wrong guess. Ratio: 0.0000");
				}
			} else {
				quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", op);
			}
		}
	}

	double ratio = 1. * (100 - max) / 100;
	ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, max, 40.0L, true) / 100.0;
	quitp(ratio, "Ratio: %.12f", ratio);

	return 0;
}
