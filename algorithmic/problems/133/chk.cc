#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    // References have nine decimal places. Accept their rounding uncertainty
    // instead of requiring an exact match to the parsed floating-point value.
    if (minimize && value <= 1e-9L) return 100.0;
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
#include <vector>
#include <cassert>

using namespace std;

const double p1 = 0.0001, p2 = 0.001, p3 = 0.01, p4 = 0.1;

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    double answ = ans.readDouble();
    double ans_guess = ouf.readDouble();
    double diff = fabs(ans_guess - answ);

    // Compute the original reciprocal score before applying the 60-point split.
    double score = 100.0 * penalized(1.0 / (1.0 + diff / (p1 * p3)));
    score = natural_log_score(score, diff, (2.0L/3.0L)*1e-6L, true);

    double score_ratio = score / 100.0;
    double unbounded_ratio = score_ratio;
    score_ratio = min(score_ratio, 1.0);

    unbounded_ratio=score_ratio;
    score=score_ratio*100.0;
    quitp(score_ratio,
          "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f, diff = %.10f",
          (long long)score, score_ratio, unbounded_ratio, diff);
}
