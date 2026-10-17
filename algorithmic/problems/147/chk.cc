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
using namespace std;

static const long long W = 10000;

struct Rect {
    long long x1, y1, x2, y2;
    long long size() const { return (x2 - x1) * (y2 - y1); }
};

static inline bool intersect(const Rect& r1, const Rect& r2) {
    return min(r1.x2, r2.x2) > max(r1.x1, r2.x1) && min(r1.y2, r2.y2) > max(r1.y1, r2.y1);
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    int n = inf.readInt();
    vector<long long> xs(n), ys(n), rs(n);
    for (int i = 0; i < n; i++) {
        xs[i] = inf.readLong();
        ys[i] = inf.readLong();
        rs[i] = inf.readLong();
    }

    vector<Rect> out(n);
    for (int i = 0; i < n; i++) {
        out[i].x1 = ouf.readLong();
        out[i].y1 = ouf.readLong();
        out[i].x2 = ouf.readLong();
        out[i].y2 = ouf.readLong();
    }
    if (!ouf.seekEof()) {
        quitf(_wa, "Too many rectangles");
    }

    double score = 0.0;
    long double area_loss = 0.0L;
    for (int i = 0; i < n; i++) {
        const Rect& r = out[i];
        if (r.x1 < 0 || r.x2 > W || r.y1 < 0 || r.y2 > W) {
            quitf(_wa, "rectangle %d is out of range", i);
        }
        if (r.x1 >= r.x2 || r.y1 >= r.y2) {
            quitf(_wa, "rectangle %d does not have positive area", i);
        }
        // Check if contains (xi, yi) according to Rust logic (xi in [x1, x2), yi in [y1, y2))
        if (!(r.x1 <= xs[i] && xs[i] < r.x2 && r.y1 <= ys[i] && ys[i] < r.y2)) {
            area_loss += 1.0L;
            continue;
        }
        for (int j = 0; j < i; j++) {
            if (intersect(out[i], out[j])) {
                quitf(_wa, "rectangles %d and %d overlap", j, i);
            }
        }
        long long si = r.size();
        long long ri = rs[i];
        double s = (double)min(si, ri) / (double)max(si, ri);
        score += 1.0 - (1.0 - s) * (1.0 - s);
        const long double mismatch = 1.0L - (long double)min(si, ri) / (long double)max(si, ri);
        area_loss += mismatch * mismatch;
    }
    score /= n;
    score *= 1e9;
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();
    long long final_score = llround(score);

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)final_score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, area_loss / n, 1.0L - (long double)best_value / 1e9L, true) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", final_score, score_ratio, score_ratio);
}
