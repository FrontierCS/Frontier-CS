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

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <bits/stdc++.h>

using i64 = long long;

int main(int argc, char* argv[]) {
	registerInteraction(argc, argv);

	int n = inf.readInt();

	int max = 1e6, tot = 0;

	while (true) {
		int action_type = ouf.readInt();
		if (action_type == 0) {
			int m = ouf.readInt(1, max - tot, "query size");
			tot += m;
			if (tot > max) {
				quitp(0., "Total size limit exceeded. Max total size: %d. Ratio: 0.0000", max);
			}

			std::vector<i64> a(m);
			for (int i = 0; i < m; i++) {
				a[i] = ouf.readLong();
				if (a[i] < 1 || a[i] > i64(1e18)) {
					quitf(_wa, "Invalid query: element %lld is out of range [%d, %lld]", a[i], 1, i64(1e18));
				}
				a[i] %= n;
			}

			// Count equal remainders using memory proportional to the query,
			// not n (which can be close to one billion).
			std::sort(a.begin(), a.end());
			i64 collisions = 0;
			i64 equal_run = 1;
			for (int i = 1; i < m; i++) {
				if (a[i] == a[i - 1]) collisions += equal_run++;
				else equal_run = 1;
			}
			println(collisions);
		} else if (action_type == 1) {
			if (ouf.readInt() == n) {
				double ratio_unbounded = (1000000.0 + 1) / (tot + 1);
				double ratio = referenceScore(ratio_unbounded);
    ratio = natural_log_score(100.0 * ratio, tot, 1000000, true) / 100.0;
                ratio_unbounded = ratio;

				quitp(ratio, "Correct guess in %d queries. Ratio: %.12f, RatioUnbounded: %.12f", tot, ratio, ratio_unbounded);
			} else {
				quitp(0., "Wrong guess. Ratio: 0.0000");
			}
			break;
		} else {
			quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", action_type);
		}
	}

	return 0;
}
