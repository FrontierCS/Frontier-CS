#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

// Use long double for better precision
using LD = long double;

const LD PI = acosl(-1.0L);
const LD EPS = 1e-12;

struct Point {
    LD x, y;
};

struct Segment {
    Point p1, p2;
    LD vx, vy, l_sq;
};

LD r;
int m;
std::vector<Segment> segments;

// Calculates the length of the union of vertical intervals at a given x-coordinate
LD get_len_at_x(LD x) {
    std::vector<std::pair<LD, LD>> intervals;
    intervals.reserve(m);

    for (int i = 0; i < m; ++i) {
        LD xa = segments[i].p1.x;
        LD ya = segments[i].p1.y;
        
        if (segments[i].l_sq < EPS) { // The segment is a point, capsule is a disk
            LD dx = x - xa;
            LD r_sq_minus_dx_sq = r * r - dx * dx;
            if (r_sq_minus_dx_sq >= 0) {
                LD h = sqrtl(r_sq_minus_dx_sq);
                intervals.push_back({ya - h, ya + h});
            }
            continue;
        }

        LD vx = segments[i].vx;
        LD vy = segments[i].vy;

        if (std::abs(vx) < EPS) { // Vertical segment
            LD dx = x - xa;
            LD r_sq_minus_dx_sq = r * r - dx * dx;
            if (r_sq_minus_dx_sq < 0) continue;
            LD h = sqrtl(r_sq_minus_dx_sq);
            intervals.push_back({std::min(segments[i].p1.y, segments[i].p2.y) - h, std::max(segments[i].p1.y, segments[i].p2.y) + h});
            continue;
        }

        LD t_lower = (x - xa - r) / vx;
        LD t_upper = (x - xa + r) / vx;
        if (vx < 0) std::swap(t_lower, t_upper);

        LD t_start = std::max((LD)0.0, t_lower);
        LD t_end = std::min((LD)1.0, t_upper);

        if (t_start > t_end + EPS) continue;

        std::vector<LD> cand_t;
        cand_t.push_back(t_start);
        cand_t.push_back(t_end);
        
        LD l = sqrtl(segments[i].l_sq);
        LD term = r * fabsl(vy) / l;

        LD t_crit_num1 = x - xa + term;
        LD t_crit1 = t_crit_num1 / vx;
        if (t_crit1 >= t_start && t_crit1 <= t_end) {
            cand_t.push_back(t_crit1);
        }

        LD t_crit_num2 = x - xa - term;
        LD t_crit2 = t_crit_num2 / vx;
        if (t_crit2 >= t_start && t_crit2 <= t_end) {
            cand_t.push_back(t_crit2);
        }

        LD y_min = 1e18, y_max = -1e18;
        for (LD t : cand_t) {
            LD px_t = xa + t * vx;
            LD py_t = ya + t * vy;
            LD dx = x - px_t;
            LD r_sq_minus_dx_sq = r * r - dx * dx;
            if (r_sq_minus_dx_sq < 0) r_sq_minus_dx_sq = 0;
            LD h = sqrtl(r_sq_minus_dx_sq);

            y_min = std::min(y_min, py_t - h);
            y_max = std::max(y_max, py_t + h);
        }
        intervals.push_back({y_min, y_max});
    }

    if (intervals.empty()) return 0.0;

    std::sort(intervals.begin(), intervals.end());

    LD union_len = 0;
    LD current_start = intervals[0].first;
    LD current_end = intervals[0].second;

    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first < current_end) {
            current_end = std::max(current_end, intervals[i].second);
        } else {
            union_len += current_end - current_start;
            current_start = intervals[i].first;
            current_end = intervals[i].second;
        }
    }
    union_len += current_end - current_start;

    return union_len;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<Point> points(n);
    LD min_x = 1e9, max_x = -1e9;
    for (int i = 0; i < n; ++i) {
        double px, py;
        std::cin >> px >> py;
        points[i] = {(LD)px, (LD)py};
    }

    std::cin >> m;
    segments.resize(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        segments[i].p1 = points[u];
        segments[i].p2 = points[v];
        segments[i].vx = segments[i].p2.x - segments[i].p1.x;
        segments[i].vy = segments[i].p2.y - segments[i].p1.y;
        segments[i].l_sq = segments[i].vx * segments[i].vx + segments[i].vy * segments[i].vy;
        min_x = std::min({min_x, points[u].x, points[v].x});
        max_x = std::max({max_x, points[u].x, points[v].x});
    }

    double r_double;
    std::cin >> r_double;
    r = r_double;

    double p1, p2, p3, p4;
    std::cin >> p1 >> p2 >> p3 >> p4;
    
    if (m == 0) {
        std::cout << std::fixed << std::setprecision(7) << 0.0 << std::endl;
        return 0;
    }

    min_x -= r;
    max_x += r;

    // Simpson's rule for numerical integration
    int N_STEPS = 50000;
    
    LD dx = (max_x - min_x) / N_STEPS;
    LD total_area = 0;

    LD y_start = get_len_at_x(min_x);
    LD y_end = get_len_at_x(max_x);
    total_area += y_start + y_end;

    for (int i = 1; i < N_STEPS; ++i) {
        LD x = min_x + i * dx;
        if (i % 2 == 1) {
            total_area += 4 * get_len_at_x(x);
        } else {
            total_area += 2 * get_len_at_x(x);
        }
    }

    total_area *= dx / 3.0;

    std::cout << std::fixed << std::setprecision(7) << (double)total_area << std::endl;

    return 0;
}