#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>

using namespace std;

const double EPS = 1e-9;

struct Point {
    double x, y;
};

struct Capsule {
    double x_min, x_max;   // active x-range [x_min, x_max]
    bool vertical;
    // For vertical capsules:
    double x0, y1, y2;     // y1 <= y2
    // For non-vertical capsules:
    double xA, yA, xB, yB, dx, dy, L;
};

double compute_union_length(double x, const vector<Capsule>& capsules) {
    vector<pair<double, double>> intervals;
    intervals.reserve(capsules.size());
    for (const auto& cap : capsules) {
        if (x < cap.x_min - EPS || x > cap.x_max + EPS) continue;
        double low, high;
        if (cap.vertical) {
            double d = cap.x0 - x;
            double t = max(0.0, cap.L*cap.L - d*d); // cap.L here stores r? Wait, careful.
            // Actually for vertical capsules, we stored y1, y2, and r is not stored in cap? We need r.
            // This is a flaw: we need r per capsule. But r is the same for all capsules? Yes, r is global.
            // So we must pass r as parameter.
            // We'll change: Capsule does not store L for vertical, we store r separately? Or we can store r in capsule.
            // Let's restructure: we'll compute intervals using r from outside.
            // I'll adjust later.
        } else {
            if (x < cap.xA - EPS) { // left cap
                double d = x - cap.xA;
                double t = max(0.0, cap.L*cap.L - d*d); // cap.L is r? No, cap.L is segment length.
                // Again, we need r.
            } else if (x > cap.xB + EPS) { // right cap
                double d = x - cap.xB;
                double t = max(0.0, cap.L*cap.L - d*d);
            } else { // strip
                double base = cap.dy * (x - cap.xA);
                low = cap.yA + (base - cap.L * cap.L) / cap.dx; // cap.L is segment length, but we need r*L? Actually we need r.
                high = cap.yA + (base + cap.L * cap.L) / cap.dx;
            }
        }
        intervals.emplace_back(low, high);
    }
    if (intervals.empty()) return 0.0;
    sort(intervals.begin(), intervals.end());
    double total = 0.0;
    double cur_l = intervals[0].first, cur_r = intervals[0].second;
    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first <= cur_r + EPS) {
            cur_r = max(cur_r, intervals[i].second);
        } else {
            total += cur_r - cur_l;
            cur_l = intervals[i].first;
            cur_r = intervals[i].second;
        }
    }
    total += cur_r - cur_l;
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cout << fixed << setprecision(10);

    int n;
    cin >> n;
    vector<Point> pts(n);
    for (int i = 0; i < n; ++i) {
        cin >> pts[i].x >> pts[i].y;
    }
    int m;
    cin >> m;
    vector<pair<int, int>> segs(m);
    for (int i = 0; i < m; ++i) {
        cin >> segs[i].first >> segs[i].second;
        --segs[i].first; --segs[i].second;
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;

    vector<Capsule> capsules;
    capsules.reserve(m);
    double global_xmin = 1e100, global_xmax = -1e100;
    for (int i = 0; i < m; ++i) {
        Point a = pts[segs[i].first];
        Point b = pts[segs[i].second];
        Capsule cap;
        if (fabs(a.x - b.x) < EPS) { // vertical
            cap.vertical = true;
            cap.x0 = a.x;
            cap.y1 = min(a.y, b.y);
            cap.y2 = max(a.y, b.y);
            cap.x_min = cap.x0 - r;
            cap.x_max = cap.x0 + r;
            cap.L = r; // reuse L to store r for vertical
        } else {
            cap.vertical = false;
            // ensure a is left endpoint
            if (a.x > b.x || (fabs(a.x - b.x) < EPS && a.y > b.y)) swap(a, b);
            cap.xA = a.x; cap.yA = a.y;
            cap.xB = b.x; cap.yB = b.y;
            cap.dx = cap.xB - cap.xA;
            cap.dy = cap.yB - cap.yA;
            cap.L = hypot(cap.dx, cap.dy);
            cap.x_min = cap.xA - r;
            cap.x_max = cap.xB + r;
        }
        global_xmin = min(global_xmin, cap.x_min);
        global_xmax = max(global_xmax, cap.x_max);
        capsules.push_back(cap);
    }

    // Number of samples - heuristic
    const int N = min(100000, max(1000, 20000000 / (int)capsules.size()));
    double step = (global_xmax - global_xmin) / N;
    double area = 0.0;
    double prev_len = 0.0;
    // compute at x = global_xmin
    {
        vector<pair<double, double>> intervals;
        intervals.reserve(capsules.size());
        for (const auto& cap : capsules) {
            double x = global_xmin;
            if (x < cap.x_min - EPS || x > cap.x_max + EPS) continue;
            double low, high;
            if (cap.vertical) {
                double d = cap.x0 - x;
                double t = max(0.0, cap.L*cap.L - d*d); // cap.L stores r
                double sqrt_t = sqrt(t);
                low = cap.y1 - sqrt_t;
                high = cap.y2 + sqrt_t;
            } else {
                if (x < cap.xA - EPS) { // left cap
                    double d = x - cap.xA;
                    double t = max(0.0, r*r - d*d);
                    double sqrt_t = sqrt(t);
                    low = cap.yA - sqrt_t;
                    high = cap.yA + sqrt_t;
                } else if (x > cap.xB + EPS) { // right cap
                    double d = x - cap.xB;
                    double t = max(0.0, r*r - d*d);
                    double sqrt_t = sqrt(t);
                    low = cap.yB - sqrt_t;
                    high = cap.yB + sqrt_t;
                } else { // strip
                    double base = cap.dy * (x - cap.xA);
                    low = cap.yA + (base - r * cap.L) / cap.dx;
                    high = cap.yA + (base + r * cap.L) / cap.dx;
                }
            }
            intervals.emplace_back(low, high);
        }
        if (!intervals.empty()) {
            sort(intervals.begin(), intervals.end());
            double cur_l = intervals[0].first, cur_r = intervals[0].second;
            for (size_t i = 1; i < intervals.size(); ++i) {
                if (intervals[i].first <= cur_r + EPS) {
                    cur_r = max(cur_r, intervals[i].second);
                } else {
                    prev_len += cur_r - cur_l;
                    cur_l = intervals[i].first;
                    cur_r = intervals[i].second;
                }
            }
            prev_len += cur_r - cur_l;
        }
    }

    for (int i = 1; i <= N; ++i) {
        double x = global_xmin + i * step;
        vector<pair<double, double>> intervals;
        intervals.reserve(capsules.size());
        for (const auto& cap : capsules) {
            if (x < cap.x_min - EPS || x > cap.x_max + EPS) continue;
            double low, high;
            if (cap.vertical) {
                double d = cap.x0 - x;
                double t = max(0.0, cap.L*cap.L - d*d);
                double sqrt_t = sqrt(t);
                low = cap.y1 - sqrt_t;
                high = cap.y2 + sqrt_t;
            } else {
                if (x < cap.xA - EPS) { // left cap
                    double d = x - cap.xA;
                    double t = max(0.0, r*r - d*d);
                    double sqrt_t = sqrt(t);
                    low = cap.yA - sqrt_t;
                    high = cap.yA + sqrt_t;
                } else if (x > cap.xB + EPS) { // right cap
                    double d = x - cap.xB;
                    double t = max(0.0, r*r - d*d);
                    double sqrt_t = sqrt(t);
                    low = cap.yB - sqrt_t;
                    high = cap.yB + sqrt_t;
                } else { // strip
                    double base = cap.dy * (x - cap.xA);
                    low = cap.yA + (base - r * cap.L) / cap.dx;
                    high = cap.yA + (base + r * cap.L) / cap.dx;
                }
            }
            intervals.emplace_back(low, high);
        }
        double cur_len = 0.0;
        if (!intervals.empty()) {
            sort(intervals.begin(), intervals.end());
            double cur_l = intervals[0].first, cur_r = intervals[0].second;
            for (size_t i = 1; i < intervals.size(); ++i) {
                if (intervals[i].first <= cur_r + EPS) {
                    cur_r = max(cur_r, intervals[i].second);
                } else {
                    cur_len += cur_r - cur_l;
                    cur_l = intervals[i].first;
                    cur_r = intervals[i].second;
                }
            }
            cur_len += cur_r - cur_l;
        }
        area += (prev_len + cur_len) * step * 0.5;
        prev_len = cur_len;
    }

    cout << area << endl;
    return 0;
}