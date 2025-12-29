#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>

using namespace std;

const double INF = 1e100;

struct Segment {
    double x1, y1, x2, y2;
    double a, b; // dx, dy
    double L, L2, rL;
    double x_start, x_end;
    double r; // brush radius
    bool is_point;

    Segment(double x1_, double y1_, double x2_, double y2_, double r_) 
        : x1(x1_), y1(y1_), x2(x2_), y2(y2_), r(r_) {
        double dx = x2 - x1;
        double dy = y2 - y1;
        a = dx;
        b = dy;
        L = sqrt(dx*dx + dy*dy);
        L2 = L*L;
        rL = r * L;
        is_point = (L == 0);
        if (is_point) {
            x_start = x1 - r;
            x_end = x1 + r;
        } else {
            x_start = min(x1, x2) - r;
            x_end = max(x1, x2) + r;
        }
    }

    // Returns the y-interval of points on the vertical line at x that are inside this capsule.
    // If no intersection, returns (INF, -INF).
    pair<double, double> get_interval(double x) const {
        double ylo = INF, yhi = -INF;
        double r2 = r * r;

        // Disk at first endpoint
        double dx1 = x - x1;
        double dx1_sq = dx1 * dx1;
        if (dx1_sq <= r2) {
            double dy = sqrt(r2 - dx1_sq);
            ylo = min(ylo, y1 - dy);
            yhi = max(yhi, y1 + dy);
        }

        // Disk at second endpoint
        double dx2 = x - x2;
        double dx2_sq = dx2 * dx2;
        if (dx2_sq <= r2) {
            double dy = sqrt(r2 - dx2_sq);
            ylo = min(ylo, y2 - dy);
            yhi = max(yhi, y2 + dy);
        }

        if (is_point) {
            return {ylo, yhi};
        }

        // Strip part (rectangle part) of the capsule
        if (a == 0) { // vertical segment
            if (fabs(dx1) <= r) {
                double y_strip_low = min(y1, y2);
                double y_strip_high = max(y1, y2);
                ylo = min(ylo, y_strip_low);
                yhi = max(yhi, y_strip_high);
            }
        } else if (b == 0) { // horizontal segment
            // check if x is between x1 and x2
            bool x_inside = ((x - x1) * (x2 - x1) >= 0 && fabs(x - x1) <= fabs(a));
            if (x_inside) {
                double y_strip_low = y1 - r;
                double y_strip_high = y1 + r;
                ylo = min(ylo, y_strip_low);
                yhi = max(yhi, y_strip_high);
            }
        } else { // general case
            double C = a * y1 + b * (x - x1);
            double y_strip_raw_low = (-rL + C) / a;
            double y_strip_raw_high = (rL + C) / a;
            if (y_strip_raw_low > y_strip_raw_high) {
                swap(y_strip_raw_low, y_strip_raw_high);
            }

            // t condition: 0 <= t <= 1
            double rhs1 = -(x - x1) * a;
            double rhs2 = L2 - (x - x1) * a;
            double y_t_low, y_t_high;
            if (b > 0) {
                y_t_low = y1 + rhs1 / b;
                y_t_high = y1 + rhs2 / b;
            } else {
                y_t_low = y1 + rhs2 / b;
                y_t_high = y1 + rhs1 / b;
            }

            double y_strip_low = max(y_strip_raw_low, y_t_low);
            double y_strip_high = min(y_strip_raw_high, y_t_high);
            if (y_strip_low <= y_strip_high) {
                ylo = min(ylo, y_strip_low);
                yhi = max(yhi, y_strip_high);
            }
        }

        if (ylo > yhi) {
            return {INF, -INF}; // empty
        }
        return {ylo, yhi};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    vector<double> px(n), py(n);
    for (int i = 0; i < n; ++i) {
        cin >> px[i] >> py[i];
    }

    int m;
    cin >> m;
    vector<Segment> segments;
    segments.reserve(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        a--; b--;
        segments.emplace_back(px[a], py[a], px[b], py[b], 0.0); // r will be set later
    }

    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;

    // Update segments with the correct radius
    for (Segment& seg : segments) {
        seg.r = r;
        // Recompute derived values that depend on r
        seg.rL = r * seg.L;
        seg.x_start = seg.is_point ? seg.x1 - r : min(seg.x1, seg.x2) - r;
        seg.x_end = seg.is_point ? seg.x1 + r : max(seg.x1, seg.x2) + r;
    }

    // Compute global x range for sweeping
    double x_min = INF, x_max = -INF;
    for (const Segment& seg : segments) {
        x_min = min(x_min, seg.x_start);
        x_max = max(x_max, seg.x_end);
    }

    // Number of samples along x-axis
    const int Nx = 5000;
    double dx = (x_max - x_min) / Nx;
    double total_area = 0.0;

    for (int i = 0; i < Nx; ++i) {
        double x = x_min + (i + 0.5) * dx; // midpoint sample
        vector<pair<double, double>> intervals;
        intervals.reserve(segments.size());

        for (const Segment& seg : segments) {
            if (x >= seg.x_start && x <= seg.x_end) {
                auto iv = seg.get_interval(x);
                if (iv.first <= iv.second) {
                    intervals.push_back(iv);
                }
            }
        }

        sort(intervals.begin(), intervals.end());

        double length = 0.0;
        double cur_l = -INF, cur_r = -INF;
        for (const auto& iv : intervals) {
            if (iv.first > cur_r) {
                if (cur_r > cur_l) {
                    length += cur_r - cur_l;
                }
                cur_l = iv.first;
                cur_r = iv.second;
            } else {
                cur_r = max(cur_r, iv.second);
            }
        }
        if (cur_r > cur_l) {
            length += cur_r - cur_l;
        }

        total_area += length * dx;
    }

    cout << fixed << setprecision(10) << total_area << endl;

    return 0;
}