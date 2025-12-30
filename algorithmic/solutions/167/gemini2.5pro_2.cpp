#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <map>
#include <cmath>
#include <list>

const int MAX_COORD = 100000;

struct Point {
    int x, y;
};

struct Fish {
    int x, y, type; // 0 for mackerel, 1 for sardine
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    auto start_time = std::chrono::high_resolution_clock::now();

    int N;
    std::cin >> N;
    std::vector<Fish> mackerels(N), sardines(N);
    std::vector<Fish> all_fish(2 * N);
    for (int i = 0; i < N; ++i) {
        std::cin >> mackerels[i].x >> mackerels[i].y;
        mackerels[i].type = 0;
        all_fish[i] = mackerels[i];
    }
    for (int i = 0; i < N; ++i) {
        std::cin >> sardines[i].x >> sardines[i].y;
        sardines[i].type = 1;
        all_fish[N + i] = sardines[i];
    }

    const int B = 250;
    const int GRID_STEP = (MAX_COORD + 1 + B - 1) / B;
    std::vector<std::vector<int>> grid_profit(B, std::vector<int>(B, 0));

    for (const auto& m : mackerels) {
        grid_profit[m.y / GRID_STEP][m.x / GRID_STEP]++;
    }
    for (const auto& s : sardines) {
        grid_profit[s.y / GRID_STEP][s.x / GRID_STEP]--;
    }

    std::vector<std::vector<int>> prefix_sum(B + 1, std::vector<int>(B + 1, 0));
    for (int i = 0; i < B; ++i) {
        for (int j = 0; j < B; ++j) {
            prefix_sum[i + 1][j + 1] = grid_profit[i][j] + prefix_sum[i][j + 1] + prefix_sum[i + 1][j] - prefix_sum[i][j];
        }
    }

    int best_r1 = 0, best_r2 = 0, best_c1 = 0, best_c2 = 0;
    long long max_profit = 0;

    for (int r1 = 0; r1 < B; ++r1) {
        for (int r2 = r1; r2 < B; ++r2) {
            long long current_sum = 0;
            int current_c1 = 0;
            for (int c2 = 0; c2 < B; ++c2) {
                long long col_sum = prefix_sum[r2 + 1][c2 + 1] - prefix_sum[r1][c2 + 1] - prefix_sum[r2 + 1][c2] + prefix_sum[r1][c2];
                current_sum += col_sum;
                if (current_sum < 0) {
                    current_sum = 0;
                    current_c1 = c2 + 1;
                }
                if (current_sum > max_profit) {
                    max_profit = current_sum;
                    best_r1 = r1;
                    best_r2 = r2;
                    best_c1 = current_c1;
                    best_c2 = c2;
                }
            }
        }
    }

    int x1 = best_c1 * GRID_STEP;
    int x2 = (best_c2 + 1) * GRID_STEP;
    int y1 = best_r1 * GRID_STEP;
    int y2 = (best_r2 + 1) * GRID_STEP;
    x2 = std::min(x2, MAX_COORD);
    y2 = std::min(y2, MAX_COORD);

    std::list<Point> polygon;
    if (max_profit > 0 && x1 < x2 && y1 < y2) {
        polygon.push_back({x1, y1});
        polygon.push_back({x2, y1});
        polygon.push_back({x2, y2});
        polygon.push_back({x1, y2});
    } else {
        polygon.push_back({0,0});
        polygon.push_back({1,0});
        polygon.push_back({1,1});
        polygon.push_back({0,1});
    }


    std::vector<bool> is_inside(2 * N);
    std::vector<Point> polygon_vec;

    auto update_inside_status = [&]() {
        polygon_vec.assign(polygon.begin(), polygon.end());
        int n = polygon_vec.size();

        auto is_on_segment = [](Point p, Point a, Point b) {
             return std::min(a.x, b.x) <= p.x && p.x <= std::max(a.x, b.x) &&
                   std::min(a.y, b.y) <= p.y && p.y <= std::max(a.y, b.y) &&
                   ( (long long)(p.x - a.x) * (b.y - a.y) == (long long)(p.y - a.y) * (b.x - a.x) );
        };

        for (int i = 0; i < 2 * N; ++i) {
            Point p = {all_fish[i].x, all_fish[i].y};
            
            bool on_boundary = false;
            for (int j = 0; j < n; ++j) {
                if (is_on_segment(p, polygon_vec[j], polygon_vec[(j + 1) % n])) {
                    on_boundary = true;
                    break;
                }
            }
            if (on_boundary) {
                is_inside[i] = true;
                continue;
            }

            int crossings = 0;
            for (int j = 0; j < n; ++j) {
                Point p1 = polygon_vec[j];
                Point p2 = polygon_vec[(j + 1) % n];
                if (p1.y == p2.y) continue;
                if (p.y < std::min(p1.y, p2.y) || p.y >= std::max(p1.y, p2.y)) continue;
                if (p.x > std::max(p1.x, p2.x) && p.x > std::max(p1.x, p2.x)) continue;
                
                double x_intersect = (double)(p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x;
                if (x_intersect > p.x) {
                    crossings++;
                }
            }
            is_inside[i] = (crossings % 2) == 1;
        }
    };
    
    update_inside_status();
    
    long long perimeter = 0;
    if(max_profit > 0 && x1 < x2 && y1 < y2) perimeter = 2LL * (x2 - x1) + 2LL * (y2 - y1);
    else perimeter = 4;

    const int MAX_VERTICES = 1000;
    const long long MAX_PERIMETER = 400000;

    for (int iter = 0; iter < 490; ++iter) {
        auto current_time = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 1950) {
            break;
        }

        if (polygon.size() >= MAX_VERTICES - 2) break;

        double best_goodness = 1e-9;
        std::list<Point>::iterator best_it = polygon.end();
        Point best_new_p1, best_new_p2;
        long long best_peri_change = 0;

        auto it = polygon.begin();
        for (size_t i = 0; i < polygon.size(); ++i) {
            auto next_it = std::next(it);
            if (next_it == polygon.end()) next_it = polygon.begin();

            Point p1 = *it;
            Point p2 = *next_it;

            for (int j = 0; j < 2 * N; ++j) {
                bool is_mackerel = all_fish[j].type == 0;
                if ((is_mackerel && is_inside[j]) || (!is_mackerel && !is_inside[j])) continue;
                
                Point f = {all_fish[j].x, all_fish[j].y};
                long long peri_change = 0;
                int score_change = 0;
                
                if (p1.x == p2.x) { // Vertical edge
                    if (f.y <= std::min(p1.y, p2.y) || f.y >= std::max(p1.y, p2.y)) continue;
                    
                    int target_x = f.x + (f.x < p1.x ? 1 : -1);
                    if (target_x < 0 || target_x > MAX_COORD) continue;

                    int x_l = std::min(p1.x, target_x), x_r = std::max(p1.x, target_x);
                    int y_l = std::min(p1.y, p2.y), y_r = std::max(p1.y, p2.y);
                    
                    int rect_profit = 0;
                    for(int k=0; k<2*N; ++k){
                        if(all_fish[k].x > x_l && all_fish[k].x < x_r && all_fish[k].y >= y_l && all_fish[k].y <= y_r){
                             rect_profit += (all_fish[k].type == 0 ? 1 : -1);
                        }
                    }
                    // p1->p2 is CCW. dy > 0 up edge, interior left. dy < 0 down, interior right
                    if ((p2.y > p1.y && target_x > p1.x) || (p2.y < p1.y && target_x < p1.x)) score_change = rect_profit;
                    else score_change = -rect_profit;
                    
                    peri_change = 2LL * std::abs(p1.x - target_x);
                } else { // Horizontal edge
                    if (f.x <= std::min(p1.x, p2.x) || f.x >= std::max(p1.x, p2.x)) continue;

                    int target_y = f.y + (f.y < p1.y ? 1 : -1);
                    if (target_y < 0 || target_y > MAX_COORD) continue;
                    
                    int x_l = std::min(p1.x, p2.x), x_r = std::max(p1.x, p2.x);
                    int y_l = std::min(p1.y, target_y), y_r = std::max(p1.y, target_y);
                    
                    int rect_profit = 0;
                    for(int k=0; k<2*N; ++k){
                        if(all_fish[k].x >= x_l && all_fish[k].x <= x_r && all_fish[k].y > y_l && all_fish[k].y < y_r){
                             rect_profit += (all_fish[k].type == 0 ? 1 : -1);
                        }
                    }
                    // dx > 0 right edge, int. up. dx < 0 left, int. down.
                    if ((p2.x > p1.x && target_y < p1.y) || (p2.x < p1.x && target_y > p1.y)) score_change = rect_profit;
                    else score_change = -rect_profit;

                    peri_change = 2LL * std::abs(p1.y - target_y);
                }
                
                if (score_change > 0 && peri_change > 0) {
                    double goodness = (double)score_change / peri_change;
                    if (goodness > best_goodness) {
                        best_goodness = goodness;
                        best_it = it;
                        best_peri_change = peri_change;
                        if (p1.x == p2.x) { // Vertical
                           int target_x = f.x + (f.x < p1.x ? 1 : -1);
                           best_new_p1 = {target_x, p1.y};
                           best_new_p2 = {target_x, p2.y};
                        } else { // Horizontal
                           int target_y = f.y + (f.y < p1.y ? 1 : -1);
                           best_new_p1 = {p1.x, target_y};
                           best_new_p2 = {p2.x, target_y};
                        }
                    }
                }
            }
            it++;
        }

        if (best_it != polygon.end() && perimeter + best_peri_change <= MAX_PERIMETER) {
            auto next_it = std::next(best_it);
            if (next_it == polygon.end()) next_it = polygon.begin();
            polygon.insert(next_it, {best_new_p1, best_new_p2});
            perimeter += best_peri_change;
            update_inside_status();
        } else {
            break;
        }
    }

    if (polygon.size() > 4) {
        std::list<Point> cleaned_polygon;
        if (!polygon.empty()) {
            for (auto it = polygon.begin(); it != polygon.end(); ++it) {
                auto prev_it = (it == polygon.begin()) ? std::prev(polygon.end()) : std::prev(it);
                auto next_it = std::next(it);
                if (next_it == polygon.end()) next_it = polygon.begin();
                
                Point p_prev = *prev_it;
                Point p_curr = *it;
                Point p_next = *next_it;
                
                if ((p_curr.x == p_prev.x && p_curr.x == p_next.x) || (p_curr.y == p_prev.y && p_curr.y == p_next.y)) {
                    // Collinear
                } else {
                    cleaned_polygon.push_back(p_curr);
                }
            }
        }
        if (cleaned_polygon.size() >= 4) {
            polygon = cleaned_polygon;
        }
    }


    std::cout << polygon.size() << "\n";
    for (const auto& p : polygon) {
        std::cout << p.x << " " << p.y << "\n";
    }

    return 0;
}