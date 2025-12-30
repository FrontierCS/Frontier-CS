#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Using double is sufficient for standard competitive programming precision.
// The time limit is very generous (20s), allowing for adaptive integration.
using Real = double;
const Real EPS = 1e-8;

struct Point {
    Real x, y;
};

struct Segment {
    int id;
    Point p1, p2;
    Real min_x, max_x;
};

int n;
vector<Point> points;
int m;
vector<Segment> segments;
Real r;
Real p_params[4];

// Calculate the length of the union of intervals at a specific x-coordinate
Real get_union_length(Real x, const vector<int>& active_indices) {
    if (active_indices.empty()) return 0.0;
    
    // Store intervals for the current x cut
    vector<pair<Real, Real>> current_intervals;
    current_intervals.reserve(active_indices.size());

    Real r2 = r * r;

    for (int idx : active_indices) {
        const Segment& seg = segments[idx];
        
        // Quick bounding box check
        if (x < seg.min_x - EPS || x > seg.max_x + EPS) continue;

        Real y_min = 1e18, y_max = -1e18;
        bool found = false;

        // Intersection with Circle 1
        Real dx1 = x - seg.p1.x;
        if (abs(dx1) <= r + EPS) {
             Real diff = r2 - dx1 * dx1;
             if (diff < 0) diff = 0;
             Real h = sqrt(diff);
             y_min = min(y_min, seg.p1.y - h);
             y_max = max(y_max, seg.p1.y + h);
             found = true;
        }

        // Intersection with Circle 2
        Real dx2 = x - seg.p2.x;
        if (abs(dx2) <= r + EPS) {
             Real diff = r2 - dx2 * dx2;
             if (diff < 0) diff = 0;
             Real h = sqrt(diff);
             y_min = min(y_min, seg.p2.y - h);
             y_max = max(y_max, seg.p2.y + h);
             found = true;
        }

        // Intersection with the rectangular body of the capsule
        Real dx = seg.p2.x - seg.p1.x;
        Real dy = seg.p2.y - seg.p1.y;
        Real len_sq = dx * dx + dy * dy;
        
        if (len_sq > EPS) {
            Real len = sqrt(len_sq);
            Real ux = dx / len;
            Real uy = dy / len;
            Real nx = -uy;
            Real ny = ux;

            // 4 corners of the rectangle
            Real c1x = seg.p1.x + r * nx, c1y = seg.p1.y + r * ny;
            Real c4x = seg.p2.x + r * nx, c4y = seg.p2.y + r * ny;
            Real c3x = seg.p2.x - r * nx, c3y = seg.p2.y - r * ny;
            Real c2x = seg.p1.x - r * nx, c2y = seg.p1.y - r * ny;

            // Helper to check intersection of line X=x with a segment
            auto check_edge = [&](Real x1, Real y1, Real x2, Real y2) {
                Real sx_min = min(x1, x2);
                Real sx_max = max(x1, x2);
                if (x >= sx_min - EPS && x <= sx_max + EPS) {
                    if (abs(x1 - x2) < EPS) {
                        y_min = min(y_min, min(y1, y2));
                        y_max = max(y_max, max(y1, y2));
                        found = true;
                    } else {
                        Real t = (x - x1) / (x2 - x1);
                        Real y = y1 + t * (y2 - y1);
                        y_min = min(y_min, y);
                        y_max = max(y_max, y);
                        found = true;
                    }
                }
            };

            check_edge(c1x, c1y, c4x, c4y);
            check_edge(c4x, c4y, c3x, c3y);
            check_edge(c3x, c3y, c2x, c2y);
            check_edge(c2x, c2y, c1x, c1y);
        }

        if (found) {
            current_intervals.push_back({y_min, y_max});
        }
    }

    if (current_intervals.empty()) return 0.0;

    // Merge overlapping intervals
    sort(current_intervals.begin(), current_intervals.end());

    Real total_len = 0;
    Real curr_l = current_intervals[0].first;
    Real curr_r = current_intervals[0].second;

    for (size_t i = 1; i < current_intervals.size(); ++i) {
        if (current_intervals[i].first < curr_r - EPS) {
            curr_r = max(curr_r, current_intervals[i].second);
        } else {
            total_len += (curr_r - curr_l);
            curr_l = current_intervals[i].first;
            curr_r = current_intervals[i].second;
        }
    }
    total_len += (curr_r - curr_l);

    return total_len;
}

Real simpson(Real l, Real r, Real fl, Real fm, Real fr) {
    return (fl + 4.0 * fm + fr) * (r - l) / 6.0;
}

Real recursive_simpson(Real l, Real r, Real fl, Real fm, Real fr, 
                       const vector<int>& active, int depth) {
    Real mid = (l + r) * 0.5;
    Real fml = get_union_length((l + mid) * 0.5, active);
    Real fmr = get_union_length((mid + r) * 0.5, active);
    
    Real est_l = simpson(l, mid, fl, fml, fm);
    Real est_r = simpson(mid, r, fm, fmr, fr);
    Real est_whole = simpson(l, r, fl, fm, fr);
    
    // Adaptive termination condition
    if (depth <= 0 || abs(est_l + est_r - est_whole) < 1e-8) {
        return est_l + est_r + (est_l + est_r - est_whole) / 15.0;
    }
    
    // Filter active segments for left and right sub-intervals
    vector<int> left_active, right_active;
    left_active.reserve(active.size());
    right_active.reserve(active.size());
    
    for (int idx : active) {
        const Segment& seg = segments[idx];
        if (seg.min_x <= mid + EPS) left_active.push_back(idx);
        if (seg.max_x >= mid - EPS) right_active.push_back(idx);
    }
    
    return recursive_simpson(l, mid, fl, fml, fm, left_active, depth - 1) +
           recursive_simpson(mid, r, fm, fmr, fr, right_active, depth - 1);
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
    segments.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        segments.push_back({i, points[u], points[v], 0, 0});
    }

    cin >> r;
    for (int i = 0; i < 4; ++i) cin >> p_params[i];

    if (m == 0) {
        cout << "0.0000000" << endl;
        return 0;
    }

    // Precompute global bounds and per-segment x-bounds
    vector<pair<Real, Real>> x_ranges;
    x_ranges.reserve(m);
    for (auto& seg : segments) {
        seg.min_x = min(seg.p1.x, seg.p2.x) - r;
        seg.max_x = max(seg.p1.x, seg.p2.x) + r;
        x_ranges.push_back({seg.min_x, seg.max_x});
    }

    // Merge x-ranges to identify disjoint components or continuous regions to integrate
    sort(x_ranges.begin(), x_ranges.end());
    vector<pair<Real, Real>> merged_ranges;
    if (!x_ranges.empty()) {
        Real cx = x_ranges[0].first;
        Real cy = x_ranges[0].second;
        for (size_t i = 1; i < x_ranges.size(); ++i) {
            if (x_ranges[i].first < cy) {
                cy = max(cy, x_ranges[i].second);
            } else {
                merged_ranges.push_back({cx, cy});
                cx = x_ranges[i].first;
                cy = x_ranges[i].second;
            }
        }
        merged_ranges.push_back({cx, cy});
    }

    vector<int> all_indices(m);
    for (int i = 0; i < m; ++i) all_indices[i] = i;

    Real total_area = 0;
    for (const auto& range : merged_ranges) {
        Real l = range.first;
        Real r_end = range.second;
        
        // Filter initial active set for this connected component
        vector<int> active;
        for (int idx : all_indices) {
            if (segments[idx].max_x > l && segments[idx].min_x < r_end) {
                active.push_back(idx);
            }
        }

        if (active.empty()) continue;

        Real mid_val = (l + r_end) * 0.5;
        Real v_l = get_union_length(l, active);
        Real v_r = get_union_length(r_end, active);
        Real v_m = get_union_length(mid_val, active);
        
        // Use a reasonable depth to ensure we catch variations
        total_area += recursive_simpson(l, r_end, v_l, v_m, v_r, active, 12);
    }

    cout << fixed << setprecision(7) << total_area << endl;

    return 0;
}