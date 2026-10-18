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

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

int main(int argc, char ** argv){
	registerInteraction(argc, argv);
    std::cout.setf(std::ios::fixed);
    std::cout.precision(20);

	int n = inf.readInt();
	println(n);

	std::vector<int> a(n);
	for (int i = 0; i < n; i++) {
		a[i] = inf.readInt();
	}
	std::vector<int> b(n);
	for (int i = 0; i < n; i++) {
		b[i] = inf.readInt();
	}

	for (int q = 0; q <= 10000; q++) {
		std::string op = ouf.readToken();
		if (op == "?") {
			long double x = ouf.readDouble();
			if (!std::isfinite(x) || x < -1e12 || x > 1e12) {
				quitf(_wa, "Invalid query: element %.12f is out of range [-1000000000000, 1000000000000]", x);
			}
			long double y = ouf.readDouble();
			if (!std::isfinite(y) || y < -1e12 || y > 1e12) {
				quitf(_wa, "Invalid query: element %.12f is out of range [-1000000000000, 1000000000000]", y);
			}

			long double sum = 0;
			for (int i = 0; i < n; i++) {
				sum += std::abs(a[i] * x - y + b[i]) / std::sqrt(a[i] * a[i] + 1);
			}

			std::cout << sum << std::endl;
		} else if (op == "!") {
			std::vector<int> ga(n);
			for (int i = 0; i < n; i++) {
				ga[i] = ouf.readInt();
			}
			std::vector<int> gb(n);
			for (int i = 0; i < n; i++) {
				gb[i] = ouf.readInt();
			}

			std::vector<int> o(n);
			std::iota(o.begin(), o.end(), 0);
			std::sort(o.begin(), o.end(), [&](int i, int j) -> bool {
				return std::pair{ga[i], gb[i]} < std::pair{ga[j], gb[j]};
			});

			for (int i = 0; i < n; i++) {
				if (ga[o[i]] != a[i] || gb[o[i]] != b[i]) {
					quitp(0., "Wrong guess. Ratio: 0.0000");
				}
			}

			double ratio = calibrated(1.0 - .7 * (q - 402.0) / (10000.0 - 402.0));
    ratio = natural_log_score(100.0 * ratio, q, 402.0L, true) / 100.0;
            double unbounded_ratio = ratio;
            quitp(ratio, "Correct guess. Ratio: %.12f, RatioUnbounded: %.12f", ratio, unbounded_ratio);
		} else {
			quitf(_wa, "Invalid action type: expected ? or !, but got %s", op.c_str());
		}
	}
	quitp(0., "Too many queries. Ratio: 0.0000");

	return 0;
}
