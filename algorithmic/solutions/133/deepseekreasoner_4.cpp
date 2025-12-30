#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>

using namespace std;

const double INF = 1e100;
const double EPS = 1e-12;

double r; // brush radius

struct Segment {
    double x1, y1, x2, y2;
    double dx, dy, L;
    double x_min, x_max;
    // precomputed for rectangle part (condition 1 and 2)
    double a_t, b_t_low, b_t_high;          // for condition 1 (t in [0,1])
    double a_band, intercept_band_low, intercept_band_high; // for condition 2 (|B| <= r*L)
    bool is_point; // zero length segment

    void precompute() {
        dx = x2 - x1;
        dy = y2 - y1;
        L = hypot(dx, dy);
        x_min = min(x1, x2) - r;
        x_max = max(x1, x2) + r;

        if (L < EPS) {
            is_point = true;
            return;
        }
        is_point