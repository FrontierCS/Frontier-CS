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

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <bits/stdc++.h>

int main(int argc, char ** argv){
	registerInteraction(argc, argv);

	std::array<std::string, 100> adj;
	for (int i = 0; i < 100; i++) {
		adj[i] = inf.readWord();
	}

	for (int q = 0; q <= 161700; q++) {
		std::string op = ouf.readToken();
		if (op == "?") {
			int a = ouf.readInt();
			if (a < 1 || a > 100) {
				quitf(_wa, "Invalid query: element %d is out of range [1, 100]", a);
			}
			a--;
			int b = ouf.readInt();
			if (b < 1 || b > 100) {
				quitf(_wa, "Invalid query: element %d is out of range [1, 100]", b);
			}
			b--;
			if (b == a) {
				quitf(_wa, "Vertices need to be pairwise different.");
			}
			int c = ouf.readInt();
			if (c < 1 || c > 100) {
				quitf(_wa, "Invalid query: element %d is out of range [1, 100]", c);
			}
			c--;
			if (c == a || c == b) {
				quitf(_wa, "Vertices need to be pairwise different.");
			}

			println((adj[a][b] == '1') + (adj[a][c] == '1') + (adj[b][c] == '1'));
		} else if (op == "!") {
			std::array<std::string, 100> guess;
			for (int i = 0; i < 100; i++) {
				guess[i] = ouf.readWord();
			}
			if (guess == adj) {
				double ratio_unbounded = 3400.0 / (q + 1);
				double ratio = referenceScore(ratio_unbounded);
    ratio = natural_log_score(100.0 * ratio, q, 3399.0L, true) / 100.0;
                ratio_unbounded = ratio;
				quitp(ratio, "Correct guess. Ratio: %.12f, RatioUnbounded: %.12f", ratio, ratio_unbounded);
			} else {
				quitp(0., "Wrong guess. Ratio: 0.0000");
			}
		}
	}
	quitp(0., "Too many queries. Ratio: 0.0000");

	return 0;
}
