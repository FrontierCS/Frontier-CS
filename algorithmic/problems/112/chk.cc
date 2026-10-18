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

#include<bits/stdc++.h>
#include "testlib.h"
using namespace std;

const double EPS_SPHERE = 1e-9;      // Very strict for sphere constraint
const double EPS_DISTANCE = 1e-6;    // For distance comparison (as per problem statement)

int n;

double distance(double x1, double y1, double z1, double x2, double y2, double z2) {
    double dx = x1 - x2;
    double dy = y1 - y2;
    double dz = z1 - z2;
    return sqrt(dx * dx + dy * dy + dz * dz);
}

bool doubleEqual(double a, double b, double eps) {
    // Handle both absolute and relative error
    if (abs(a) < eps && abs(b) < eps) return true;
    return abs(a - b) <= eps * max(1.0, max(abs(a), abs(b)));
}


// Map normalized performance to the reference-anchored score, without a cap.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * std::log(r));
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    n = inf.readInt();

    // Read reference answer
    double ref_answer = ans.readDouble();
    ensuref(std::isfinite(ref_answer) && ref_answer > 0.0, "Reference distance must be finite and positive");

    // Read participant's output
    if (ouf.seekEof()) {
        quitf(_wa, "No output provided");
    }

    double claimed_min_dist = ouf.readDouble();

    if (claimed_min_dist < 0) {
        quitf(_wa, "Minimum distance cannot be negative: %.10f", claimed_min_dist);
    }

    vector<tuple<double, double, double>> points;

    // Read all n points
    for (int i = 0; i < n; i++) {
        if (ouf.seekEof()) {
            quitf(_wa, "Expected %d points, but only found %d", n, i);
        }

        double x = ouf.readDouble();
        double y = ouf.readDouble();
        double z = ouf.readDouble();

        // Check if point is within unit sphere (strict tolerance)
        double dist_from_origin = sqrt(x * x + y * y + z * z);
        if (dist_from_origin > 1.0 + EPS_SPHERE) {
            quitf(_wa, "Point %d at (%.10f, %.10f, %.10f) is outside the unit sphere (distance from origin: %.15f)",
                  i + 1, x, y, z, dist_from_origin);
        }

        points.push_back({x, y, z});
    }

    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output found after %d points", n);
    }

    // Calculate actual minimum pairwise distance
    double actual_min_dist = 1e18;
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            double d = distance(get<0>(points[i]), get<1>(points[i]), get<2>(points[i]),
                              get<0>(points[j]), get<1>(points[j]), get<2>(points[j]));
            actual_min_dist = min(actual_min_dist, d);
        }
    }

    // Verify claimed distance matches actual distance (looser tolerance)
    if (!doubleEqual(actual_min_dist, claimed_min_dist, EPS_DISTANCE)) {
        quitf(_wa, "Claimed minimum distance %.10f does not match actual minimum distance %.10f (difference: %.10f)",
              claimed_min_dist, actual_min_dist, abs(claimed_min_dist - actual_min_dist));
    }

    // Calculate score
    // Subtract logarithms above the reference to avoid overflowing the ratio.
    double score_ratio = claimed_min_dist <= ref_answer
        ? referenceScore(claimed_min_dist / ref_answer)
        : 0.6 + 0.02 * (std::log(claimed_min_dist) - std::log(ref_answer));
    score_ratio = natural_log_score(100.0 * score_ratio, claimed_min_dist, ref_answer, false) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Min distance: %.10f. Ratio: %.12f, RatioUnbounded: %.12f", claimed_min_dist, score_ratio, unbounded_ratio);

    return 0;
}
