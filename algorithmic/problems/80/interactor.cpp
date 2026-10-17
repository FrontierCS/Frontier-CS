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

	int n = inf.readInt(), m = inf.readInt();
	println(m);

	std::vector adj(n, std::vector<int>(m));
	for (int i = 0; i < n; i++) {
		for (int j = 0; j < m; j++) {
			adj[i][j] = inf.readInt();
		}
	}

	std::vector type(n, std::string("center"));
	std::vector pos(n, 0);
	int x = 0, cnt = 0;
	std::vector vis(n, std::vector(m, false));

	for (int q = 0; q <= 50000; q++) {
		if (cnt == n * m) {
			println("treasure");

			double ratio = 1. * (50000 - q) / 50000;
			ratio=penalized(ratio);
    ratio = natural_log_score(100.0 * ratio, q, 20000, true) / 100.0;
			quitp(ratio, "Ratio: %.12f", ratio);
		}
		println(type[x]);

		int c = ouf.readInt();
		if (c < 0 || c >= m) {
			quitf(_wa, "Invalid query: element %d is out of range [0, %d]", c, m - 1);
		}
		std::string s = ouf.readWord();
		if (s != "left" && s != "right") {
			quitf(_wa, "Invalid query: %s should be left or right.", s.c_str());
		}
		int t = ouf.readInt();
		if (t < 0 || t >= m) {
			quitf(_wa, "Invalid query: element %d is out of range [0, %d]", t, m - 1);
		}

		int y = adj[x][(pos[x] + t) % m];
		if (!vis[x][(pos[x] + t) % m]) {
			vis[x][(pos[x] + t) % m] = true;
			cnt++;
		}
		type[x] = s;
		pos[x] = (pos[x] + c) % m;
		x = y;
	}
	quitp(0., "Too many queries. Ratio: 0.0000");

	return 0;
}
