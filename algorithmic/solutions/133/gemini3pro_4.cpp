#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Represents a capsule formed by stroking a line segment with radius R
struct Capsule {
    double x1, y1;
    double x2, y2;
    double dx, dy; // x2-x1, y2-y1
    double min_x, max_x; // Bounding box in x
};

int n, m;
double R;
double p1, p2, p3, p4;
vector<Capsule> capsules;

// Scracthpad for intervals merging
vector<pair<double, double>> intervals;

// Grid optimization
// Coordinate range is approx [-105, 105].
// We use buckets to limit the number of capsules checked during integration.
const double BUCKET_SIZE = 5.0; 
const double MIN_COORD = -150.0;
const int NUM_BUCKETS = 100; // Covers [-150, 350]
vector<int> buckets[NUM_BUCKETS];

// Helper to compute the Y interval of a capsule at a specific X
pair<double, double> get_interval(const Capsule& c, double x) {
    // Check bounding box with epsilon
    if (x < c.min_x - 1e-9 || x > c.max_x + 1e-9) return {1e18, -1e18};

    double D = x - c.x1;
    double t_min = 0.0, t_max = 1.0;

    // Determine valid range of parameter t in [0, 1] such that |(x-x1) - t*dx| <= R
    if (abs(c.dx) < 1e-9) {
        if (abs(D) > R) return {1e18, -1e18};
        // t remains [0, 1]
    } else {
        // |D - t*dx| <= R  =>  D-R <= t*dx <= D+R
        double v1 = (D - R) / c.dx;
        double v2 = (D + R) / c.dx;
        if (c.dx > 0) {
            t_min = max(t_min, v1);
            t_max = min(t_max, v2);
        } else {
            t_min = max(t_min, v2);
            t_max = min(t_max, v1);
        }
    }

    if (t_min > t_max + 1e-9) return {1e18, -1e18};

    double y_low = 1e18, y_high = -1e18;

    // Function to evaluate Y at parameter t and sign s (+1 or -1 for upper/lower part of circle)
    auto update = [&](double t, int sign) {
        double Z = D - t * c.dx;
        double root = R*R - Z*Z;
        if (root < 0) root = 0;
        double val = c.y1 + t * c.dy + sign * sqrt(root);
        if (val < y_low) y_low = val;
        if (val > y_high) y_high = val;
    };

    // Check endpoints of the valid t interval
    update(t_min, 1); update(t_min, -1);
    if (abs(t_max - t_min) > 1e-9) {
        update(t_max, 1); update(t_max, -1);
    }

    // Check critical points where derivative is zero
    // Z_opt = +/- K*R / sqrt(1+K^2), where K = -dy/dx
    if (abs(c.dx) > 1e-9) {
        double K = -c.dy / c.dx;
        double factor = R / sqrt(1.0 + K*K);
        double Z_crit = abs(K) * factor; 
        
        // We need to check both +Z_crit and -Z_crit
        // Corresponding t = (D - Z) / dx
        double t_crit1 = (D - Z_crit) / c.dx;
        if (t_crit1 > t_min + 1e-9 && t_crit1 < t_max - 1e-9) {
            update(t_crit1, 1); update(t_crit1, -1);
        }
        double t_crit2 = (D + Z_crit) / c.dx;
        if (t_crit2 > t_min + 1e-9 && t_crit2 < t_max - 1e-9) {
            update(t_crit2, 1); update(t_crit2, -1);
        }
    }

    return {y_low, y_high};
}

// Global pointer to candidates for current integration step
const vector<int>* current_candidates = nullptr;

// Calculates the length of the union of intervals at coordinate x
double calc_len(double x) {
    intervals.clear();
    for (int idx : *current_candidates) {
        const auto& c = capsules[idx];
        // Only process if x is within the capsule's x-range
        if (x >= c.min_x && x <= c.max_x) {
            pair<double, double> p = get_interval(c, x);
            if (p.first <= p.second) {
                intervals.push_back(p);
            }
        }
    }

    if (intervals.empty()) return 0.0;
    sort(intervals.begin(), intervals.end());

    double total = 0;
    double l = intervals[0].first;
    double r = intervals[0].second;

    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first > r) {
            total += (r - l);
            l = intervals[i].first;
            r = intervals[i].second;
        } else {
            if (intervals[i].second > r) r = intervals[i].second;
        }
    }
    total += (r - l);
    return total;
}

// Adaptive Simpson's Integration
double simpson(double l, double r, double fl, double fmid, double fr, int depth) {
    double mid = (l + r) * 0.5;
    double lmid = (l + mid) * 0.5;
    double rmid = (mid + r) * 0.5;
    double flmid = calc_len(lmid);
    double frmid = calc_len(rmid);
    
    double S_whole = (r - l) / 6.0 * (fl + 4.0 * fmid + fr);
    double S_left = (mid - l) / 6.0 * (fl + 4.0 * flmid + fmid);
    double S_right = (r - mid) / 6.0 * (fmid + 4.0 * frmid + fr);
    
    // Check convergence or depth limit
    if (depth <= 0 || abs(S_left + S_right - S_whole) < 1e-7) {
        return S_left + S_right + (S_left + S_right - S_whole) / 15.0;
    }
    return simpson(l, mid, fl, flmid, fmid, depth - 1) + 
           simpson(mid, r, fmid, frmid, fr, depth - 1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    
    struct Pt { double x, y; };
    vector<Pt> pts(n);
    for(int i=0; i<n; ++i) cin >> pts[i].x >> pts[i].y;
    
    cin >> m;
    capsules.reserve(m);
    
    vector<pair<int, int>> segs(m);
    for(int i=0; i<m; ++i) {
        cin >> segs[i].first >> segs[i].second;
    }
    cin >> R;
    cin >> p1 >> p2 >> p3 >> p4;

    if (m == 0) {
        cout << "0.0000000" << endl;
        return 0;
    }

    double min_all = 1e18, max_all = -1e18;

    for(int i=0; i<m; ++i) {
        int u = segs[i].first - 1;
        int v = segs[i].second - 1;
        Capsule c;
        c.x1 = pts[u].x; c.y1 = pts[u].y;
        c.x2 = pts[v].x; c.y2 = pts[v].y;
        c.dx = c.x2 - c.x1;
        c.dy = c.y2 - c.y1;
        
        c.min_x = min(c.x1, c.x2) - R;
        c.max_x = max(c.x1, c.x2) + R;
        
        capsules.push_back(c);
        
        if (c.min_x < min_all) min_all = c.min_x;
        if (c.max_x > max_all) max_all = c.max_x;
        
        // Populate buckets
        int b_start = max(0, int((c.min_x - MIN_COORD) / BUCKET_SIZE));
        int b_end = min(NUM_BUCKETS - 1, int((c.max_x - MIN_COORD) / BUCKET_SIZE));
        
        for(int b = b_start; b <= b_end; ++b) {
            buckets[b].push_back(i);
        }
    }

    double total_area = 0;
    int start_b = max(0, int((min_all - MIN_COORD) / BUCKET_SIZE));
    int end_b = min(NUM_BUCKETS - 1, int((max_all - MIN_COORD) / BUCKET_SIZE));
    
    for (int b = start_b; b <= end_b; ++b) {
        if (buckets[b].empty()) continue;
        
        current_candidates = &buckets[b];
        
        double l = MIN_COORD + b * BUCKET_SIZE;
        double r = l + BUCKET_SIZE;
        
        // Clip to global bounds
        l = max(l, min_all);
        r = min(r, max_all);
        
        if (l >= r - 1e-9) continue;
        
        double fl = calc_len(l);
        double fr = calc_len(r);
        double fmid = calc_len((l+r)*0.5);
        
        total_area += simpson(l, r, fl, fmid, fr, 18);
    }

    cout << fixed << setprecision(7) << total_area << endl;
    
    return 0;
}