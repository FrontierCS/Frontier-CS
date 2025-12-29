#include <iostream>
#include <iomanip>
#include <cmath>
#include <vector>
#include <map>
#include <stack>
#include <algorithm>
#include <cassert>
using namespace std;

const int Q_MAX = 10000;
const int Q_MIN = 402;
const long long COORD_LIMIT = 1000000000000LL;
const int A_LIMIT = 10000;
const int B_LIMIT = 10000;

int n;
int query_count = 0;
map<pair<double, double>, double> cache;

double query_point(double x, double y) {
    auto key = make_pair(x, y);
    if (cache.count(key)) return cache[key];
    if (query_count >= Q_MAX) {
        // Should not happen, but just in case
        cerr << "Too many queries!" << endl;
    }
    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    double res;
    cin >> res;
    query_count++;
    cache[key] = res;
    return res;
}

double query_f(double y) {
    return query_point(0.0, y);
}

double query_g(double x) {
    return query_point(x, 0.0);
}

struct Breakpoint {
    double t;
    double delta;   // slope change (positive)
};

vector<Breakpoint> find_breakpoints(double l, double r,
                                    double (*query)(double),
                                    double small_interval,
                                    double slope_eps) {
    vector<Breakpoint> res;
    struct Interval {
        double l, r, fl, fr;
    };
    stack<Interval> stk;
    double fl = query(l);
    double fr = query(r);
    stk.push({l, r, fl, fr});

    while (!stk.empty()) {
        Interval it = stk.top(); stk.pop();
        double l = it.l, r = it.r, fl = it.fl, fr = it.fr;
        if (r - l < small_interval) {
            // small interval -> try to detect breakpoint
            double eps2 = (r - l) * 1e-3;
            double l2 = l + eps2;
            double r2 = r - eps2;
            double fl2 = query(l2);
            double fr2 = query(r2);
            double slope_left = (fl2 - fl) / (l2 - l);
            double slope_right = (fr - fr2) / (r - r2);
            if (fabs(slope_right - slope_left) > slope_eps) {
                // breakpoint exists
                double t = (fr - fl - slope_right * r + slope_left * l) /
                           (slope_left - slope_right);
                double delta = fabs(slope_right - slope_left);
                res.push_back({t, delta});
            }
            continue;
        }
        double m = (l + r) * 0.5;
        double fm = query(m);
        double slope_left = (fm - fl) / (m - l);
        double slope_right = (fr - fm) / (r - m);
        if (fabs(slope_left - slope_right) > slope_eps) {
            // non-linear -> split
            stk.push({m, r, fm, fr});
            stk.push({l, m, fl, fm});
        }
        // else linear -> ignore
    }
    return res;
}

int main() {
    cin >> n;
    const double FY_MIN = -B_LIMIT - 10;
    const double FY_MAX = B_LIMIT + 10;
    const double GX_MIN = -A_LIMIT - 10;
    const double GX_MAX = A_LIMIT + 10;

    // ----- Phase 1: breakpoints along y-axis (x=0) -----
    vector<Breakpoint> f_bps = find_breakpoints(
        FY_MIN, FY_MAX, query_f, 0.5, 1e-6);

    // Merge f breakpoints (they should be near integers)
    map<int, double> f_map;
    for (auto &bp : f_bps) {
        int b = (int)round(bp.t);
        if (b < -B_LIMIT || b > B_LIMIT) continue;
        f_map[b] += bp.delta;
    }
    vector<pair<int, double>> f_breaks;
    for (auto &p : f_map) {
        f_breaks.push_back(p);
    }

    // ----- Phase 2: breakpoints along x-axis (y=0) -----
    vector<Breakpoint> g_bps = find_breakpoints(
        GX_MIN, GX_MAX, query_g, 1e-6, 1e-7);

    // Merge g breakpoints (close together)
    sort(g_bps.begin(), g_bps.end(),
         [](const Breakpoint &a, const Breakpoint &b) { return a.t < b.t; });
    vector<pair<double, double>> g_breaks;
    for (size_t i = 0; i < g_bps.size();) {
        double t_sum = g_bps[i].t;
        double d_sum = g_bps[i].delta;
        size_t j = i + 1;
        while (j < g_bps.size() && fabs(g_bps[j].t - g_bps[i].t) < 1e-4) {
            t_sum += g_bps[j].t;
            d_sum += g_bps[j].delta;
            ++j;
        }
        g_breaks.push_back({t_sum / (j - i), d_sum});
        i = j;
    }

    // ----- Recover lines -----
    vector<pair<int, int>> lines; // (a, b)

    // remaining delta_f for each f breakpoint
    vector<double> rem_delta_f;
    for (auto &fb : f_breaks) rem_delta_f.push_back(fb.second);

    // process g breakpoints
    vector<bool> used_g(g_breaks.size(), false);
    for (size_t gi = 0; gi < g_breaks.size(); ++gi) {
        double x = g_breaks[gi].first;
        double delta_g = g_breaks[gi].second;
        int best_fi = -1;
        double best_score = 1e100;
        for (size_t fi = 0; fi < f_breaks.size(); ++fi) {
            int b = f_breaks[fi].first;
            double a_exact = -b / x;
            if (fabs(a_exact) > A_LIMIT + 0.5) continue;
            int a = (int)round(a_exact);
            if (a < -A_LIMIT || a > A_LIMIT) continue;
            double c = 1.0 / sqrt(a * a + 1.0);
            double pred_delta_g = 2.0 * c * fabs(a);
            double pred_delta_f = 2.0 * c;
            // score: relative error in delta_g + distance to integer a
            double score = fabs(pred_delta_g - delta_g) / delta_g +
                           fabs(a_exact - a) * 1e4; // weight for integer closeness
            if (score < best_score) {
                best_score = score;
                best_fi = fi;
            }
        }
        if (best_fi != -1 && best_score < 0.1) {
            int b = f_breaks[best_fi].first;
            double a_exact = -b / g_breaks[gi].first;
            int a = (int)round(a_exact);
            double c = 1.0 / sqrt(a * a + 1.0);
            double pred_delta_f = 2.0 * c;
            if (pred_delta_f <= rem_delta_f[best_fi] + 1e-3) {
                rem_delta_f[best_fi] -= pred_delta_f;
                lines.push_back({a, b});
                used_g[gi] = true;
            }
        }
    }

    // add lines with a = 0 from remaining delta_f
    for (size_t fi = 0; fi < f_breaks.size(); ++fi) {
        int b = f_breaks[fi].first;
        int cnt = (int)round(rem_delta_f[fi] / 2.0);
        // safety: cnt should be non-negative integer
        if (cnt < 0) cnt = 0;
        for (int i = 0; i < cnt; ++i) {
            lines.push_back({0, b});
        }
    }

    // if we still have fewer than n lines, we may have missed some.
    // but we trust the detection. Output the lines we found.
    // The problem guarantees that lines are distinct and not parallel.
    // We must output exactly n lines. If we have extra, remove; if less, add dummy? Should not happen.
    // For safety, we will output first n lines we have (or pad with zeros if necessary).
    lines.resize(n, {0, 0});

    // output answer
    cout << "!";
    for (auto &line : lines) cout << " " << line.first;
    for (auto &line : lines) cout << " " << line.second;
    cout << endl;

    return 0;
}