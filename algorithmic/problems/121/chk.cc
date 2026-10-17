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

int main(int argc, char* argv[]) {
	registerTestlibCmd(argc, argv);

	double actual=ouf.readDouble(), reference=ans.readDouble();
    double ratio = reference==0.0 ? (actual==0.0 ? 1.0 : 0.0)
        : std::max(1 - 10 * std::abs(actual / reference - 1), 0.);
	ratio=penalized(ratio);
    if (reference != 0.0) {
        const long double error = std::abs(((long double)actual - (long double)reference) / (long double)reference);
        ratio = natural_log_score(100.0 * ratio, error, 0.04L, true) / 100.0;
    }
	quitp(ratio, "Ratio: %.12f", ratio);

	return 0;
}
