#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constants
const double EPS_INTERSECTION = 1e-9;
const double EPS_SIMPSON = 1e-10;

struct Point {
    double x, y;
};

struct Capsule {
    int id;
    Point A, B; 
    double min_x, max_x; 
    double ax, ay, bx, by;
    double nx, ny; // normal vector scaled by r
};

int n, m;
double r_radius;
vector<Point> points;
vector<Capsule> capsules;

// Returns the interval of y coordinates [y_min, y_max] for the capsule at x = X
// Returns true if intersection is non-empty
bool get_interval(const Capsule& c, double X, double& y_min, double& y_max) {
    if (X < c.min_x || X > c.max_x) return false;

    y_min = 1e18; 
    y_max = -1e18;
    bool found = false;

    // Check intersection with Circle A
    double dx_a = X - c.ax;
    if (abs(dx_a) <= r_radius) {
        double delta = sqrt(max(0.0, r_radius*r_radius - dx_a*dx_a));
        y_min = min(y_min, c.ay - delta);
        y_max = max(y_max, c.ay + delta);
        found = true;
    }

    // Check intersection with Circle B
    double dx_b = X - c.bx;
    if (abs(dx_b) <= r_radius) {
        double delta = sqrt(max(0.0, r_radius*r_radius - dx_b*dx_b));
        y_min = min(y_min, c.by - delta);
        y_max = max(y_max, c.by + delta);
        found = true;
    }

    // Check intersection with the rectangular region connecting the circles
    // The rectangle vertices (outer tangents)
    double p1x = c.ax + c.nx, p1y = c.ay + c.ny;
    double p2x = c.bx + c.nx, p2y = c.by + c.ny;
    double p3x = c.bx - c.nx, p3y = c.by - c.ny;
    double p4x = c.ax - c.nx, p4y = c.ay - c.ny;

    auto check_seg = [&](double x1, double y1, double x2, double y2) {
        // Bounding box of segment check first
        if (X < min(x1, x2) || X > max(x1, x2)) return;
        
        if (abs(x1 - x2) < EPS_INTERSECTION) {
            // Vertical segment. If X is close, take the whole y range.
            if (abs(X - x1) < EPS_INTERSECTION) {
                y_min = min(y_min, min(y1, y2));
                y_max = max(y_max, max(y1, y2));
                found = true;
            }
        } else {
            // Find y at x=X
            double t = (X - x1) / (x2 - x1);
            // t must be in [0, 1] approximately
            if (t >= -EPS_INTERSECTION && t <= 1.0 + EPS_INTERSECTION) {
                double y = y1 + t * (y2 - y1);
                y_min = min(y_min, y);
                y_max = max(y_max, y);
                found = true;
            }
        }
    };

    check_seg(p1x, p1y, p2x, p2y);
    check_seg(p2x, p2y, p3x, p3y);
    check_seg(p3x, p3y, p4x, p4y);
    check_seg(p4x, p4y, p1x, p1y);

    return found;
}

// Computes the length of the union of intervals at x = X
double calc_union_length(double X, const vector<int>& active_indices) {
    if (active_indices.empty()) return 0.0;
    
    // Static vector to reduce allocation overhead. Safe for single-threaded non-reentrant use.
    // Since Simpson calls calc_union_length sequentially (not nested), this is safe.
    static vector<pair<double, double>> intervals; 
    intervals.clear();
    
    double y1, y2;
    for (int idx : active_indices) {
        if (get_interval(capsules[idx], X, y1, y2)) {
            if (y1 < y2) intervals.push_back({y1, y2});
        }
    }

    if (intervals.empty()) return 0.0;

    sort(intervals.begin(), intervals.end());

    double total_len = 0.0;
    double start = intervals[0].first;
    double end = intervals[0].second;

    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first < end + EPS_INTERSECTION) { 
            end = max(end, intervals[i].second);
        } else {
            total_len += (end - start);
            start = intervals[i].first;
            end = intervals[i].second;
        }
    }
    total_len += (end - start);
    return total_len;
}

double simpson(double L, double R, double fL, double fmid, double fR, const vector<int>& indices, int depth) {
    double mid = (L + R) / 2;
    double len = R - L;
    double approx = (fL + 4 * fmid + fR) * len / 6;
    
    if (depth <= 0) return approx;

    vector<int> relevant;
    relevant.reserve(indices.size());
    for (int idx : indices) {
        if (capsules[idx].max_x >= L && capsules[idx].min_x <= R) {
            relevant.push_back(idx);
        }
    }
    
    if (relevant.empty()) return 0.0;

    double lm = (L + mid) / 2;
    double rm = (mid + R) / 2;
    double flm = calc_union_length(lm, relevant);
    double frm = calc_union_length(rm, relevant);
    
    double left_simpson = (fL + 4 * flm + fmid) * (mid - L) / 6;
    double right_simpson = (fmid + 4 * frm + fR) * (R - mid) / 6;
    
    double error = abs(left_simpson + right_simpson - approx);
    
    // Depth check ensures we don't stop too early (we want at least 5 levels of recursion from depth 25)
    if (error < EPS_SIMPSON && depth < 20) {
        return left_simpson + right_simpson + (left_simpson + right_simpson - approx) / 15.0;
    }
    
    return simpson(L, mid, fL, flm, fmid, relevant, depth - 1) +
           simpson(mid, R, fmid, frm, fR, relevant, depth - 1);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n)) return 0;
    
    points.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> points[i].x >> points[i].y;
    }
    
    cin >> m;
    struct Seg { int u, v; };
    vector<Seg> segments(m);
    for(int i=0; i<m; ++i) cin >> segments[i].u >> segments[i].v;
    
    cin >> r_radius;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    
    if (m == 0) {
        cout << "0.0000000" << endl;
        return 0;
    }

    capsules.reserve(m);
    double min_total_x = 1e18, max_total_x = -1e18;

    for (int i = 0; i < m; ++i) {
        int u = segments[i].u;
        int v = segments[i].v;
        
        Point A = points[u];
        Point B = points[v];
        
        Capsule c;
        c.id = i;
        c.A = A;
        c.B = B;
        c.ax = A.x; c.ay = A.y;
        c.bx = B.x; c.by = B.y;
        c.min_x = min(A.x, B.x) - r_radius;
        c.max_x = max(A.x, B.x) + r_radius;
        
        min_total_x = min(min_total_x, c.min_x);
        max_total_x = max(max_total_x, c.max_x);
        
        double dx = B.x - A.x;
        double dy = B.y - A.y;
        double len_sq = dx*dx + dy*dy;
        
        if (len_sq > 1e-12) {
            double len = sqrt(len_sq);
            c.nx = -dy / len * r_radius;
            c.ny = dx / len * r_radius;
        } else {
            c.nx = 0;
            c.ny = 0;
        }
        
        capsules.push_back(c);
    }
    
    vector<int> all_indices(capsules.size());
    for (size_t i = 0; i < capsules.size(); ++i) all_indices[i] = i;
    
    double fL = calc_union_length(min_total_x, all_indices);
    double fmid = calc_union_length((min_total_x + max_total_x)/2.0, all_indices);
    double fR = calc_union_length(max_total_x, all_indices);
    
    cout << fixed << setprecision(7) << simpson(min_total_x, max_total_x, fL, fmid, fR, all_indices, 25) << endl;
    
    return 0;
}