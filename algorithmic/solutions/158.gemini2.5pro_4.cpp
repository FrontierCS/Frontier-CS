#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>

// Timer
auto start_time = std::chrono::high_resolution_clock::now();
const double TIME_LIMIT = 2.8;

struct Point {
    long long x, y;
};

long long cross_product(Point a, Point b, Point c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

long long dist_sq(Point a, Point b) {
    return (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
}

std::vector<Point> convex_hull(std::vector<Point>& points) {
    int n = points.size();
    if (n <= 2) return points;
    std::sort(points.begin(), points.end(), [](Point a, Point b) {
        return a.x < b.x || (a.x == b.x && a.y < b.y);
    });
    std::vector<Point> hull;
    for (int i = 0; i < n; ++i) {
        while (hull.size() >= 2 && cross_product(hull[hull.size()-2], hull.back(), points[i]) <= 0) {
            hull.pop_back();
        }
        hull.push_back(points[i]);
    }
    for (int i = n - 2, t = hull.size() + 1; i >= 0; i--) {
        while (hull.size() >= t && cross_product(hull[hull.size()-2], hull.back(), points[i]) <= 0) {
            hull.pop_back();
        }
        hull.push_back(points[i]);
    }
    hull.pop_back();
    return hull;
}

bool is_strictly_inside(Point p, const std::vector<Point>& polygon) {
    if (polygon.empty() || polygon.size() < 3) return false;
    int n = polygon.size();
    for (int i = 0; i < n; ++i) {
        if (cross_product(polygon[i], polygon[(i + 1) % n], p) <= 0) {
            return false;
        }
    }
    return true;
}

const int GRID_SIZE = 200;
const int CAKE_RADIUS = 10000;
const int CELL_SIZE = 2 * CAKE_RADIUS / GRID_SIZE + 1;
std::vector<int> grid[GRID_SIZE][GRID_SIZE];

int get_grid_coord(long long val) {
    return std::max(0, std::min(GRID_SIZE - 1, (int)((val + CAKE_RADIUS) / CELL_SIZE)));
}

struct Cut {
    Point p1, p2;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, K;
    std::cin >> N >> K;
    std::vector<int> a(11);
    for (int i = 1; i <= 10; ++i) std::cin >> a[i];

    std::vector<Point> strawberries(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> strawberries[i].x >> strawberries[i].y;
        grid[get_grid_coord(strawberries[i].x)][get_grid_coord(strawberries[i].y)].push_back(i);
    }

    std::vector<int> needed = a;
    std::vector<bool> is_removed(N, false);
    std::vector<Cut> cuts;
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    while (cuts.size() < K) {
        auto current_time = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration<double>(current_time - start_time).count() > TIME_LIMIT) break;

        std::vector<int> available_indices;
        for(int i=0; i<N; ++i) if(!is_removed[i]) available_indices.push_back(i);
        if (available_indices.empty()) break;

        double best_score = -1.0;
        std::vector<int> best_group_indices;
        int best_d = -1;
        int best_cuts_needed = K + 1;

        int C = 50;
        if (available_indices.size() < C) C = available_indices.size();
        std::shuffle(available_indices.begin(), available_indices.end(), rng);

        for (int i = 0; i < C; ++i) {
            int p_idx = available_indices[i];
            for (int d = 10; d >= 1; --d) {
                if (needed[d] == 0) continue;
                if (available_indices.size() < d) continue;

                std::vector<std::pair<long long, int>> dists;
                for (int other_idx : available_indices) {
                    if (p_idx == other_idx) continue;
                    dists.push_back({dist_sq(strawberries[p_idx], strawberries[other_idx]), other_idx});
                }
                
                std::partial_sort(dists.begin(), dists.begin() + (d-1), dists.end());
                
                std::vector<int> current_group_indices;
                current_group_indices.push_back(p_idx);
                for(int j=0; j<d-1; ++j) current_group_indices.push_back(dists[j].second);

                int cuts_needed = 0;
                bool is_separable = false;
                std::vector<Point> current_group_points;
                for(int idx : current_group_indices) current_group_points.push_back(strawberries[idx]);

                if (d <= 2) {
                    cuts_needed = 4;
                    if (cuts.size() + cuts_needed > K) continue;
                    
                    long long min_x = 20001, max_x = -20001, min_y = 20001, max_y = -20001;
                    for(const auto& p : current_group_points) {
                        min_x = std::min(min_x, p.x); max_x = std::max(max_x, p.x);
                        min_y = std::min(min_y, p.y); max_y = std::max(max_y, p.y);
                    }
                    min_x--; max_x++; min_y--; max_y++;

                    bool clean = true;
                    int min_gx = get_grid_coord(min_x), max_gx = get_grid_coord(max_x);
                    int min_gy = get_grid_coord(min_y), max_gy = get_grid_coord(max_y);
                    for(int gx = min_gx; gx <= max_gx && clean; ++gx) for(int gy = min_gy; gy <= max_gy && clean; ++gy) {
                        for(int s_idx : grid[gx][gy]) {
                            if(is_removed[s_idx]) continue;
                            bool in_group = false;
                            for(int gi : current_group_indices) if(gi == s_idx) in_group = true;
                            if(in_group) continue;
                            
                            Point sp = strawberries[s_idx];
                            if(sp.x >= min_x && sp.x <= max_x && sp.y >= min_y && sp.y <= max_y) {
                                clean = false; break;
                            }
                        }
                    }
                    if(clean) is_separable = true;
                } else { // d >= 3
                    std::vector<Point> hull = convex_hull(current_group_points);
                    cuts_needed = hull.size();
                    if (cuts.size() + cuts_needed > K || cuts_needed < 3) continue;

                    long long min_x = 20001, max_x = -20001, min_y = 20001, max_y = -20001;
                    for(const auto& p : hull) {
                        min_x = std::min(min_x, p.x); max_x = std::max(max_x, p.x);
                        min_y = std::min(min_y, p.y); max_y = std::max(max_y, p.y);
                    }
                    
                    bool clean = true;
                    int min_gx = get_grid_coord(min_x), max_gx = get_grid_coord(max_x);
                    int min_gy = get_grid_coord(min_y), max_gy = get_grid_coord(max_y);
                    for(int gx = min_gx; gx <= max_gx && clean; ++gx) for(int gy = min_gy; gy <= max_gy && clean; ++gy) {
                        for(int s_idx : grid[gx][gy]) {
                            if(is_removed[s_idx]) continue;
                            bool in_group = false;
                            for(int gi : current_group_indices) if(gi == s_idx) in_group = true;
                            if(in_group) continue;
                            if (is_strictly_inside(strawberries[s_idx], hull)) {
                                clean = false; break;
                            }
                        }
                    }
                    if(clean) is_separable = true;
                }
                if (is_separable) {
                    double score = (double)d * d / cuts_needed;
                    if (score > best_score) {
                        best_score = score; best_group_indices = current_group_indices;
                        best_d = d; best_cuts_needed = cuts_needed;
                    }
                }
            }
        }
        if (best_d != -1) {
            if (best_d <= 2) {
                std::vector<Point> group_points;
                for(int idx : best_group_indices) group_points.push_back(strawberries[idx]);
                long long min_x = 20001, max_x = -20001, min_y = 20001, max_y = -20001;
                for(const auto& p : group_points) {
                    min_x = std::min(min_x, p.x); max_x = std::max(max_x, p.x);
                    min_y = std::min(min_y, p.y); max_y = std::max(max_y, p.y);
                }
                min_x--; max_x++; min_y--; max_y++;
                long long V = 100000;
                cuts.push_back({{min_x, -V}, {min_x, V}}); cuts.push_back({{max_x, -V}, {max_x, V}});
                cuts.push_back({{-V, min_y}, {V, min_y}}); cuts.push_back({{-V, max_y}, {V, max_y}});
            } else {
                std::vector<Point> group_points;
                for(int idx : best_group_indices) group_points.push_back(strawberries[idx]);
                std::vector<Point> hull = convex_hull(group_points);
                for (size_t i = 0; i < hull.size(); ++i) {
                    cuts.push_back({hull[i], hull[(i + 1) % hull.size()]});
                }
            }
            for (int idx : best_group_indices) is_removed[idx] = true;
            needed[best_d]--;
        } else {
            break;
        }
    }
    std::cout << cuts.size() << std::endl;
    for (const auto& cut : cuts) {
        std::cout << cut.p1.x << " " << cut.p1.y << " " << cut.p2.x << " " << cut.p2.y << std::endl;
    }
    return 0;
}