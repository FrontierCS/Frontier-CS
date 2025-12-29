#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Constant for PI and Epsilon
const double PI = acos(-1.0);
const double EPS = 1e-8;
const double SIMPSON_EPS = 1e-7;

// Structs for geometry
struct Point {
    double x, y;
};

struct Capsule {
    int id;
    double x1, y1, x2, y2;
    double len_sq;
    double min_x, max_x;
};

// Global variables
int n, m;
vector<Point> points;
vector<Capsule> capsules;
double R;

// Interval structure for union length calculation
struct Interval {
    double l, r;
    bool operator<(const Interval& other) const {
        return l < other.l;
    }
};

// Function to calculate the length of the union of active capsules at a specific x coordinate
double get_union_length(double x, const vector<int>& indices) {
    vector<Interval> intervals;
    intervals.reserve(indices.size());

    double R2 = R * R;

    for (int idx : indices) {
        const Capsule& cap = capsules[idx];
        
        // Skip if x is outside the bounding box (redundant if filtered, but safe)
        if (x < cap.min_x || x > cap.max_x) continue;

        double y_min = 1e18;
        double y_max = -1e18;
        bool active = false;

        // Check intersection with Circle 1 (at x1, y1)
        double dx1 = x - cap.x1;
        double dx1_sq = dx1 * dx1;
        if (dx1_sq <= R2) {
            double h = sqrt(R2 - dx1_sq);
            y_min = min(y_min, cap.y1 - h);
            y_max = max(y_max, cap.y1 + h);
            active = true;
        }

        // Check intersection with Circle 2 (at x2, y2)
        double dx2 = x - cap.x2;
        double dx2_sq = dx2 * dx2;
        if (dx2_sq <= R2) {
            double h = sqrt(R2 - dx2_sq);
            y_min = min(y_min, cap.y2 - h);
            y_max = max(y_max, cap.y2 + h);
            active = true;
        }

        // Check intersection with the rectangular body of the capsule
        if (cap.len_sq > 1e-12) {
            double dx = cap.x2 - cap.x1;
            double dy = cap.y2 - cap.y1;
            
            // Check if vertical
            if (abs(dx) > 1e-9) {
                // The strip defined by the two parallel lines
                // y range for the infinite strip at x
                // Center line y at x: y_c = y1 + (x-x1)*dy/dx
                // Vertical half-width: W = R * sqrt(dx^2+dy^2) / |dx|
                // Range: [y_c - W, y_c + W]
                
                // Optimized calculation:
                // Strip boundaries eq: (y-y1)dx - (x-x1)dy = +/- R*L
                // y*dx = (x-x1)dy + y1*dx +/- R*L
                double cross = (x - cap.x1) * dy + cap.y1 * dx;
                double delta = R * sqrt(cap.len_sq);
                
                double y_s1 = (cross - delta) / dx;
                double y_s2 = (cross + delta) / dx;
                double y_strip_min = min(y_s1, y_s2);
                double y_strip_max = max(y_s1, y_s2);
                
                // Projection constraints: 0 <= (x-x1)dx + (y-y1)dy <= L^2
                // y*dy ranges from -(x-x1)dx to L^2 - (x-x1)dx
                double proj_base = -(x - cap.x1) * dx;
                double y_proj_min = -1e18, y_proj_max = 1e18;
                
                if (dy > 1e-9) {
                    y_proj_min = proj_base / dy + cap.y1;
                    y_proj_max = (proj_base + cap.len_sq) / dy + cap.y1;
                } else if (dy < -1e-9) {
                    y_proj_max = proj_base / dy + cap.y1;
                    y_proj_min = (proj_base + cap.len_sq) / dy + cap.y1;
                } else {
                    // Horizontal segment (dy approx 0)
                    // Valid only if 0 <= (x-x1)dx <= L^2 (i.e. x between x1 and x2)
                    double t_num = (x - cap.x1) * dx;
                    if (t_num < -1e-9 || t_num > cap.len_sq + 1e-9) {
                        y_proj_min = 1e18; // Invalid
                    }
                }
                
                double y_rect_min = max(y_strip_min, y_proj_min);
                double y_rect_max = min(y_strip_max, y_proj_max);
                
                if (y_rect_min <= y_rect_max) {
                    y_min = min(y_min, y_rect_min);
                    y_max = max(y_max, y_rect_max);
                    active = true;
                }
            } else {
                // Vertical segment (dx approx 0)
                // Strip condition: dist to line <= R => |x-x1| <= R
                if (abs(x - cap.x1) <= R) {
                    // Projection: y between y1 and y2
                    double y_p1 = min(cap.y1, cap.y2);
                    double y_p2 = max(cap.y1, cap.y2);
                    y_min = min(y_min, y_p1);
                    y_max = max(y_max, y_p2);
                    active = true;
                }
            }
        }

        if (active) {
            intervals.push_back({y_min, y_max});
        }
    }

    if (intervals.empty()) return 0.0;

    // Sort and merge intervals
    sort(intervals.begin(), intervals.end());

    double total_len = 0;
    double current_l = intervals[0].l;
    double current_r = intervals[0].r;

    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].l < current_r) {
            current_r = max(current_r, intervals[i].r);
        } else {
            total_len += (current_r - current_l);
            current_l = intervals[i].l;
            current_r = intervals[i].r;
        }
    }
    total_len += (current_r - current_l);
    return total_len;
}

// Adaptive Simpson's Integration
double adaptive_simpson(double L, double R, double fl, double fr, double fm, const vector<int>& indices, int depth) {
    double mid = (L + R) / 2;
    double h = R - L;
    
    double lm = (L + mid) / 2;
    double rm = (mid + R) / 2;
    
    // Evaluate at midpoints of sub-intervals
    double flm = get_union_length(lm, indices);
    double frm = get_union_length(rm, indices);
    
    double approx_whole = (h / 6) * (fl + 4 * fm + fr);
    double approx_left = (h / 12) * (fl + 4 * flm + fm);
    double approx_right = (h / 12) * (fm + 4 * frm + fr);
    
    // Check convergence or max depth
    if (depth <= 0 || abs(approx_left + approx_right - approx_whole) < 15 * SIMPSON_EPS) {
        return approx_left + approx_right + (approx_left + approx_right - approx_whole) / 15.0;
    }
    
    // Filter indices for recursive calls to improve performance
    vector<int> left_indices;
    left_indices.reserve(indices.size());
    for (int idx : indices) {
        if (capsules[idx].max_x > L && capsules[idx].min_x < mid) {
             left_indices.push_back(idx);
        }
    }
    
    vector<int> right_indices;
    right_indices.reserve(indices.size());
    for (int idx : indices) {
        if (capsules[idx].max_x > mid && capsules[idx].min_x < R) {
            right_indices.push_back(idx);
        }
    }
    
    return adaptive_simpson(L, mid, fl, fm, flm, left_indices, depth - 1) +
           adaptive_simpson(mid, R, fm, fr, frm, right_indices, depth - 1);
}

// Wrapper for integration
double integrate(double L, double R, const vector<int>& indices) {
    if (indices.empty()) return 0.0;
    double mid = (L + R) / 2;
    double fl = get_union_length(L, indices);
    double fr = get_union_length(R, indices);
    double fm = get_union_length(mid, indices);
    return adaptive_simpson(L, R, fl, fr, fm, indices, 20); // Depth limit
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
        cap.id = i;
        cap.x1 = points[u].x;
        cap.y1 = points[u].y;
        cap.x2 = points[v].x;
        cap.y2 = points[v].y;
        
        // Precompute length squared
        double dx = cap.x2 - cap.x1;
        double dy = cap.y2 - cap.y1;
        cap.len_sq = dx * dx + dy * dy;
        
        capsules.push_back(cap);
    }
    
    cin >> R;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    
    if (m == 0) {
        cout << fixed << setprecision(7) << 0.0 << endl;
        return 0;
    }

    // Precompute bounding boxes with radius R
    double min_all_x = 1e18, max_all_x = -1e18;
    for (auto& cap : capsules) {
        double c_min_x = min(cap.x1, cap.x2) - R;
        double c_max_x = max(cap.x1, cap.x2) + R;
        cap.min_x = c_min_x;
        cap.max_x = c_max_x;
        min_all_x = min(min_all_x, c_min_x);
        max_all_x = max(max_all_x, c_max_x);
    }

    // Divide the integration range into blocks to speed up processing of large M
    double width = max_all_x - min_all_x;
    if (width < 1e-9) {
        cout << fixed << setprecision(7) << 0.0 << endl;
        return 0;
    }
    
    int num_blocks = 128; // Tuning parameter
    double block_size = width / num_blocks;
    double total_area = 0;
    
    for (int i = 0; i < num_blocks; ++i) {
        double b_start = min_all_x + i * block_size;
        double b_end = min_all_x + (i + 1) * block_size;
        if (i == num_blocks - 1) b_end = max_all_x;
        
        vector<int> block_indices;
        // Collect capsules relevant to this block
        for (int j = 0; j < m; ++j) {
            if (capsules[j].max_x > b_start && capsules[j].min_x < b_end) {
                block_indices.push_back(j);
            }
        }
        
        if (!block_indices.empty()) {
            total_area += integrate(b_start, b_end, block_indices);
        }
    }

    cout << fixed << setprecision(7) << total_area << endl;

    return 0;
}