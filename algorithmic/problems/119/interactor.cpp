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
#include <bits/stdc++.h>

int main(int argc, char ** argv){
	registerInteraction(argc, argv);

	int n = inf.readInt();
	println(n);

	std::vector<int> o(n);
	for (int i = 0; i < n; i++) {
		o[i] = inf.readInt();
	}

	for (int q = 0; q <= 600; q++) {
		std::string op = ouf.readToken();
		if (op == "?") {
			int res = ouf.readInt();
			if (res < 0 || res >= 1000000007) {
				quitf(_wa, "Invalid query: element %d is out of range [1, 1000000006]", res);
			}

			for (int i = 0; i < n; i++) {
				int x = ouf.readInt();
				if (x < 0 || x >= 1000000007) {
					quitf(_wa, "Invalid query: element %d is out of range [1, 1000000006]", x);
				}

				res = (o[i] == 0 ? (res + x) % 1000000007 : 1ll * res * x % 1000000007);
			}

			println(res);
		} else if (op == "!") {
			std::vector<int> guess(n);
			for (int i = 0; i < n; i++) {
				guess[i] = ouf.readInt();
			}

			if (guess == o) {
				double ratio_unbounded = (40.0 + 1) / (q + 1);
				double ratio = ratio_unbounded <= 1.0 ? 0.6*ratio_unbounded : 0.6 + 0.02*std::log(ratio_unbounded);
    ratio = natural_log_score(100.0 * ratio, q, 40.0L, true) / 100.0;
                ratio_unbounded = ratio;
				quitp(ratio, "Correct guess. Ratio: %.12f, RatioUnbounded: %.12f", ratio, ratio_unbounded);
			} else {
				quitp(0., "Wrong guess. Ratio: 0.0000");
			}
		} else {
			quitf(_wa, "Invalid action type: expected ? or !, but got %s", op.c_str());
		}
	}
	quitp(0., "Too many queries. Ratio: 0.0000");

	return 0;
}
