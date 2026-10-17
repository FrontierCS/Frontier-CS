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

	std::string s = inf.readWord();
	int q = 0;

	while (true) {
		int op = ouf.readInt();
		if (op == 0) {
			if (++q > 200) {
				quitp(0., "Too many queries. Ratio: 0.0000");
			}

			int m = ouf.readInt();
			if (m < 1 || m > 1000) {
				quitf(_wa, "Invalid query: element %d is out of range [1, 1000]", m);
			}

			std::string t;
			for (int i = 0; i < m; i++) {
				int j = ouf.readInt();
				if (j < 1 || j > n) {
					quitf(_wa, "Invalid query: element %d is out of range [1, %d]", j, n);
				}
				j--;

				t += s[j];
			}

			std::vector sum(m + 1, 0);
			for (int i = 0; i < m; i++) {
				sum[i + 1] = sum[i] + (t[i] == '(' ? 1 : -1);
			}

			std::vector<int> stk;
			std::vector cnt(2 * m + 1, 0);
			int tot = 0;

			for (int i = 0; i <= m; i++) {
				while (!stk.empty() && stk.back() > sum[i]) {
					cnt[m + stk.back()]--;
					stk.pop_back();
				}
				tot += cnt[m + sum[i]]++;
				stk.push_back(sum[i]);
			}

			println(tot);
		} else if (op == 1) {
			if (ouf.readWord() == s) {
				double ratio = 1. * (200 - q) / 200;
				ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, q, 80, true) / 100.0;
				quitp(ratio, "Correct Solution. Ratio: %.12f", ratio);
			} else {
				quitp(0., "Wrong guess. Ratio: 0.0000");
			}
		} else {
			quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", op);
		}
	}

	return 0;
}
