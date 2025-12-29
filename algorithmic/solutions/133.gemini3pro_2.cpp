#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constants
const double PI = acos(-1.0);
const double EPS = 1e-8; // For geometry checks
const double SIMPSON_EPS = 1e-6; // For integration accuracy

struct Point {
    double x, y;
};

struct Capsule {
    Point a, b;
    double r;
    // Precomputed values for bounding box
    double min_x, max_x;
    // Precomputed geometry
    double dx, dy, len, inv_len;
    double perp_x, perp_y; // Scaled by r (vector perpendicular to AB)
};

int n, m;
double r_val;
vector<Point> points;
vector<Capsule> capsules;

// Function to compute y-intervals of a capsule at a given x
// Adds interval [y1, y2] to the list if the line x intersects the capsule
inline void get_capsule_interval(const Capsule& cap, double x, vector<pair<double, double>>& intervals) {
    if (x < cap.min_x - EPS || x > cap.max_x + EPS) return;

    double y_min = 1e18, y_max = -1e18;
    bool found = false;

    // Check Circle A: (x-ax)^2 + (y-ay)^2 <= r^2
    double dist_sq_a = (x - cap.a.x) * (x - cap.a.x);
    if (dist_sq_a <= cap.r * cap.r + EPS) {
        double delta = sqrt(max(0.0, cap.r * cap.r - dist_sq_a));
        y_min = min(y_min, cap.a.y - delta);
        y_max = max(y_max, cap.a.y + delta);
        found = true;
    }
    
    // Check Circle B
    double dist_sq_b = (x - cap.b.x) * (x - cap.b.x);
    if (dist_sq_b <= cap.r * cap.r + EPS) {
        double delta = sqrt(max(0.0, cap.r * cap.r - dist_sq_b));
        y_min = min(y_min, cap.b.y - delta);
        y_max = max(y_max, cap.b.y + delta);
        found = true;
    }

    // Check Rectangle part
    // The rectangle vertices are A+perp, B+perp, B-perp, A-perp.
    // It's a convex polygon. We intersect the vertical line X=x with its 4 edges.
    // Only process if the segment has non-zero length
    if (cap.len > EPS) {
        // Edge 1: (A+perp) -> (B+perp). Parametric: x(t) = A.x + perp.x + t*dx
        if (abs(cap.dx) > EPS) {
            double t = (x - (cap.a.x + cap.perp_x)) / cap.dx;
            if (t >= -EPS && t <= 1.0 + EPS) {
                double y = cap.a.y + cap.perp_y + t * cap.dy;
                y_min = min(y_min, y);
                y_max = max(y_max, y);
                found = true;
            }
            
            // Edge 2: (A-perp) -> (B-perp)
            t = (x - (cap.a.x - cap.perp_x)) / cap.dx;
            if (t >= -EPS && t <= 1.0 + EPS) {
                double y = cap.a.y - cap.perp_y + t * cap.dy;
                y_min = min(y_min, y);
                y_max = max(y_max, y);
                found = true;
            }
        }
        
        // Edge 3 & 4 (Chords): (B+perp)->(B-perp) and (A-perp)->(A+perp)
        // These are needed especially when dx is close to 0 (vertical capsule)
        // x(t) for chord at B: B.x + perp.x + t*(-2*perp.x)
        if (abs(cap.perp_x) > EPS) {
             // Chord at B
             double t = (x - (cap.b.x + cap.perp_x)) / (-2.0 * cap.perp_x);
             if (t >= -EPS && t <= 1.0 + EPS) {
                 double y = cap.b.y + cap.perp_y + t * (-2.0 * cap.perp_y);
                 y_min = min(y_min, y);
                 y_max = max(y_max, y);
                 found = true;
             }
             // Chord at A
             t = (x - (cap.a.x - cap.perp_x)) / (2.0 * cap.perp_x);
             if (t >= -EPS && t <= 1.0 + EPS) {
                 double y = cap.a.y - cap.perp_y + t * (2.0 * cap.perp_y);
                 y_min = min(y_min, y);
                 y_max = max(y_max, y);
                 found = true;
             }
        }
    }

    if (found) {
        intervals.push_back({y_min, y_max});
    }
}

// Compute length of union of intervals at x
double get_union_length(double x, const vector<int>& active_capsules) {
    // Static buffer to avoid reallocation in recursion (thread-local if needed, but here single thread)
    // However, vector inside function is safer for recursion logic unless we pass buffer. 
    // Given depth and structure, creating vector here is acceptable.
    static vector<pair<double, double>> intervals; 
    // We can't use static if this function is called recursively in a way that interleaves usage?
    // asr calls get_union_length sequentially. It's safe.
    intervals.clear();
    intervals.reserve(active_capsules.size());
    
    for (int idx : active_capsules) {
        get_capsule_interval(capsules[idx], x, intervals);
    }
    if (intervals.empty()) return 0.0;
    
    sort(intervals.begin(), intervals.end());
    
    double total = 0.0;
    double current_start = intervals[0].first;
    double current_end = intervals[0].second;
    
    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first < current_end + EPS) {
            current_end = max(current_end, intervals[i].second);
        } else {
            total += (current_end - current_start);
            current_start = intervals[i].first;
            current_end = intervals[i].second;
        }
    }
    total += (current_end - current_start);
    return total;
}

// Adaptive Simpson Integration
double asr(double l, double r, double fl, double fr, double fm, const vector<int>& active, double eps) {
    double mid = (l + r) / 2.0;
    double lm = (l + mid) / 2.0;
    double rm = (mid + r) / 2.0;
    double flm = get_union_length(lm, active);
    double frm = get_union_length(rm, active);
    
    double simpson_whole = (r - l) / 6.0 * (fl + 4.0 * fm + fr);
    double simpson_left = (mid - l) / 6.0 * (fl + 4.0 * flm + fm);
    double simpson_right = (r - mid) / 6.0 * (fm + 4.0 * frm + fr);
    
    // Check error
    if (abs(simpson_left + simpson_right - simpson_whole) <= 15.0 * eps) {
        // Richardson extrapolation for better precision
        return simpson_left + simpson_right + (simpson_left + simpson_right - simpson_whole) / 15.0;
    }
    
    return asr(l, mid, fl, flm, fm, active, eps / 2.0) + asr(mid, r, fm, frm, fr, active, eps / 2.0);
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
    capsules.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        Capsule cap;
        cap.a = points[u];
        cap.b = points[v];
        capsules.push_back(cap);
    }
    
    double p1, p2, p3, p4;
    cin >> r_val >> p1 >> p2 >> p3 >> p4;
    
    double global_min_x = 1e18, global_max_x = -1e18;
    
    // Precompute capsule properties
    for (auto& cap : capsules) {
        cap.r = r_val;
        cap.dx = cap.b.x - cap.a.x;
        cap.dy = cap.b.y - cap.a.y;
        double l2 = cap.dx * cap.dx + cap.dy * cap.dy;
        cap.len = sqrt(l2);
        if (cap.len > EPS) {
            cap.inv_len = 1.0 / cap.len;
            cap.perp_x = -cap.dy * cap.inv_len * r_val;
            cap.perp_y = cap.dx * cap.inv_len * r_val;
        } else {
            cap.inv_len = 0;
            cap.perp_x = 0;
            cap.perp_y = 0;
        }
        
        cap.min_x = min(cap.a.x, cap.b.x) - r_val;
        cap.max_x = max(cap.a.x, cap.b.x) + r_val;
        
        global_min_x = min(global_min_x, cap.min_x);
        global_max_x = max(global_max_x, cap.max_x);
    }
    
    if (m == 0) {
        cout << "0.0000000" << endl;
        return 0;
    }
    
    // Use buckets to optimize integration
    double bucket_size = 1.0; 
    int min_bucket = floor(global_min_x / bucket_size);
    int max_bucket = floor(global_max_x / bucket_size);
    
    int num_buckets = max_bucket - min_bucket + 1;
    vector<vector<int>> buckets(num_buckets);
    
    for (int i = 0; i < m; ++i) {
        int b_start = floor(capsules[i].min_x / bucket_size);
        int b_end = floor(capsules[i].max_x / bucket_size);
        b_start = max(b_start, min_bucket);
        b_end = min(b_end, max_bucket);
        for (int b = b_start; b <= b_end; ++b) {
            buckets[b - min_bucket].push_back(i);
        }
    }
    
    double total_area = 0.0;
    
    for (int b = 0; b < num_buckets; ++b) {
        if (buckets[b].empty()) continue;
        
        double l = (min_bucket + b) * bucket_size;
        double r = l + bucket_size;
        
        l = max(l, global_min_x);
        r = min(r, global_max_x);
        if (l >= r - EPS) continue;
        
        double fl = get_union_length(l, buckets[b]);
        double fr = get_union_length(r, buckets[b]);
        double fm = get_union_length((l + r) / 2.0, buckets[b]);
        
        total_area += asr(l, r, fl, fr, fm, buckets[b], SIMPSON_EPS);
    }
    
    cout << fixed << setprecision(7) << total_area << endl;
    
    return 0;
}