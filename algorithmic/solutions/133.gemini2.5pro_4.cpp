#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <random>
#include <chrono>
#include <algorithm>
#include <ctime>

struct Point {
    double x, y;
};

struct Segment {
    Point p1, p2;
    double len_sq;
};

// Computes the squared distance from a point to a line segment.
// Using squared distances avoids costly square root operations.
double dist_sq_to_segment(const Point& p, const Segment& s) {
    if (s.len_sq == 0.0) {
        return (p.x - s.p1.x) * (p.x - s.p1.x) + (p.y - s.p1.y) * (p.y - s.p1.y);
    }
    // Project point p onto the line containing segment s
    double t = ((p.x - s.p1.x) * (s.p2.x - s.p1.x) + (p.y - s.p1.y) * (s.p2.y - s.p1.y)) / s.len_sq;
    // Clamp t to [0, 1] to find the closest point on the segment
    t = std::max(0.0, std::min(1.0, t));
    double closest_x = s.p1.x + t * (s.p2.x - s.p1.x);
    double closest_y = s.p1.y + t * (s.p2.y - s.p1.y);
    // Return squared distance to this closest point
    return (p.x - closest_x) * (p.x - closest_x) + (p.y - closest_y) * (p.y - closest_y);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<Point> points(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> points[i].x >> points[i].y;
    }

    int m;
    std::cin >> m;

    std::vector<Segment> segments(m);
    std::vector<bool> point_used(n, false);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        segments[i].p1 = points[u];
        segments[i].p2 = points[v];
        double dx = segments[i].p2.x - segments[i].p1.x;
        double dy = segments[i].p2.y - segments[i].p1.y;
        segments[i].len_sq = dx * dx + dy * dy;
        point_used[u] = true;
        point_used[v] = true;
    }

    double r;
    std::cin >> r;

    double p1, p2, p3, p4;
    std::cin >> p1 >> p2 >> p3 >> p4;

    if (m == 0) {
        std::cout << std::fixed << std::setprecision(7) << 0.0 << std::endl;
        return 0;
    }
    
    // Determine bounding box based on points actually used
    double min_coord_x = 101.0, max_coord_x = -101.0, min_coord_y = 101.0, max_coord_y = -101.0;
    bool first_point = true;
    for (int i = 0; i < n; ++i) {
        if (point_used[i]) {
            if (first_point) {
                min_coord_x = points[i].x; max_coord_x = points[i].x;
                min_coord_y = points[i].y; max_coord_y = points[i].y;
                first_point = false;
            } else {
                min_coord_x = std::min(min_coord_x, points[i].x);
                max_coord_x = std::max(max_coord_x, points[i].x);
                min_coord_y = std::min(min_coord_y, points[i].y);
                max_coord_y = std::max(max_coord_y, points[i].y);
            }
        }
    }
    
    // Expand bounding box by radius r
    min_coord_x -= r;
    max_coord_x += r;
    min_coord_y -= r;
    max_coord_y += r;

    double bbox_width = max_coord_x - min_coord_x;
    double bbox_height = max_coord_y - min_coord_y;
    double bbox_area = bbox_width * bbox_height;

    long long covered_count = 0;
    long long total_samples = 0;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_real_distribution<double> dist_x(min_coord_x, max_coord_x);
    std::uniform_real_distribution<double> dist_y(min_coord_y, max_coord_y);
    
    double r_sq = r * r;

    // Run simulation for a fixed duration to adapt to test case difficulty
    auto time_limit = 19.5 * CLOCKS_PER_SEC;
    auto clock_start = clock();

    while(clock() - clock_start < time_limit) {
        const int batch_size = 1024; // Process in batches to reduce clock() overhead
        int batch_covered = 0;
        for(int k = 0; k < batch_size; ++k) {
            Point p = {dist_x(rng), dist_y(rng)};
            
            for (int j = 0; j < m; ++j) {
                if (dist_sq_to_segment(p, segments[j]) <= r_sq) {
                    batch_covered++;
                    break;
                }
            }
        }
        covered_count += batch_covered;
        total_samples += batch_size;
    }
    
    double covered_area = 0.0;
    if (total_samples > 0) {
        covered_area = bbox_area * static_cast<double>(covered_count) / total_samples;
    }

    std::cout << std::fixed << std::setprecision(7) << covered_area << std::endl;

    return 0;
}