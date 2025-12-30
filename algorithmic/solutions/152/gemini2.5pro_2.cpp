#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>

struct Point {
    int x, y;
};

int manhattan_dist(Point p1, Point p2) {
    return std::abs(p1.x - p2.x) + std::abs(p1.y - p2.y);
}

struct Order {
    int id;
    Point pickup;
    Point delivery;
};

struct TourPoint {
    Point pos;
    int order_id; 
    int type; // 0: depot, 1: pickup, 2: delivery
};

std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

class Timer {
public:
    Timer() : start_time(std::chrono::steady_clock::now()) {}
    long long elapsed_ms() {
        auto end_time = std::chrono::steady_clock::now();
        return std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();
    }
private:
    std::chrono::steady_clock::time_point start_time;
};

long long calculate_tour_cost(const std::vector<int>& tour, const std::vector<TourPoint>& points) {
    long long cost = 0;
    for (size_t i = 0; i < tour.size(); ++i) {
        cost += manhattan_dist(points[tour[i]].pos, points[tour[(i + 1) % tour.size()]].pos);
    }
    return cost;
}

std::vector<TourPoint> build_tour_points(const std::vector<int>& selection, const std::vector<Order>& all_orders) {
    std::vector<TourPoint> points;
    points.push_back({{400, 400}, 0, 0}); // Depot at index 0
    for (int order_idx : selection) {
        points.push_back({all_orders[order_idx-1].pickup, order_idx, 1});
    }
    for (int order_idx : selection) {
        points.push_back({all_orders[order_idx-1].delivery, order_idx, 2});
    }
    return points;
}

std::vector<int> build_greedy_tour(const std::vector<TourPoint>& points) {
    int n = points.size();
    std::vector<int> tour;
    tour.push_back(0);

    std::vector<bool> visited(n, false);
    visited[0] = true;

    std::vector<bool> pickup_done(1001, false);

    for (int i = 0; i < n - 1; ++i) {
        int last_idx = tour.back();
        int best_next_idx = -1;
        int min_dist = 1e9;

        for (int j = 1; j < n; ++j) {
            if (!visited[j]) {
                if (points[j].type == 2 && !pickup_done[points[j].order_id]) {
                    continue;
                }
                int d = manhattan_dist(points[last_idx].pos, points[j].pos);
                if (d < min_dist) {
                    min_dist = d;
                    best_next_idx = j;
                }
            }
        }
        
        tour.push_back(best_next_idx);
        visited[best_next_idx] = true;
        if (points[best_next_idx].type == 1) {
            pickup_done[points[best_next_idx].order_id] = true;
        }
    }
    return tour;
}

void optimize_tour_2opt(std::vector<int>& tour, const std::vector<TourPoint>& points, const Timer& timer, long long time_limit) {
    int n = tour.size();
    if (n <= 3) return;

    std::vector<int> partner(n);
    for(int i = 1; i <= 50; ++i) {
        partner[i] = i + 50;
        partner[i+50] = i;
    }
    
    std::vector<int> pos(n);
    bool improved = true;
    while (improved) {
        if (timer.elapsed_ms() > time_limit) break;
        improved = false;
        
        for (int i = 0; i < n; ++i) pos[tour[i]] = i;

        for (int i = 0; i < n; ++i) {
            for (int j = i + 2; j < n; ++j) {
                if (i == 0 && j == n - 1) continue;

                int i_next = (i + 1) % n;
                int j_next = (j + 1) % n;
                
                long long current_cost = manhattan_dist(points[tour[i]].pos, points[tour[i_next]].pos) + manhattan_dist(points[tour[j]].pos, points[tour[j_next]].pos);
                long long new_cost = manhattan_dist(points[tour[i]].pos, points[tour[j]].pos) + manhattan_dist(points[tour[i_next]].pos, points[tour[j_next]].pos);

                if (new_cost < current_cost) {
                    bool ok = true;
                    for (int k = i + 1; k <= j; ++k) {
                        int p_idx = tour[k];
                        if (points[p_idx].type == 1) { 
                            int partner_p_idx = partner[p_idx];
                            if (pos[partner_p_idx] > i && pos[partner_p_idx] <= j) {
                                ok = false;
                                break;
                            }
                        }
                    }

                    if (ok) {
                        std::reverse(tour.begin() + i + 1, tour.begin() + j + 1);
                        improved = true;
                        goto next_iteration;
                    }
                }
            }
        }
        next_iteration:;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    Timer timer;
    const long long TIME_LIMIT = 2950;

    std::vector<Order> all_orders(1000);
    for (int i = 0; i < 1000; ++i) {
        all_orders[i].id = i + 1;
        std::cin >> all_orders[i].pickup.x >> all_orders[i].pickup.y >> all_orders[i].delivery.x >> all_orders[i].delivery.y;
    }

    std::vector<int> best_selection;
    long long min_cost = -1;

    for (int k = 0; k < 10 && timer.elapsed_ms() < 500; ++k) {
        std::vector<int> current_selection;
        std::vector<int> p(1000);
        std::iota(p.begin(), p.end(), 0);
        std::shuffle(p.begin(), p.end(), rng);
        for(int i=0; i<50; ++i) current_selection.push_back(p[i]+1);

        for (int iter = 0; iter < 5; ++iter) {
            Point p_cent = {0,0}, d_cent = {0,0};
            for (int id : current_selection) {
                p_cent.x += all_orders[id-1].pickup.x; p_cent.y += all_orders[id-1].pickup.y;
                d_cent.x += all_orders[id-1].delivery.x; d_cent.y += all_orders[id-1].delivery.y;
            }
            p_cent.x /= 50; p_cent.y /= 50; d_cent.x /= 50; d_cent.y /= 50;

            std::vector<std::pair<int, int>> scores;
            for (int i = 0; i < 1000; ++i) {
                scores.push_back({manhattan_dist(all_orders[i].pickup, p_cent) + manhattan_dist(all_orders[i].delivery, d_cent), i+1});
            }
            std::sort(scores.begin(), scores.end());
            
            current_selection.clear();
            for(int i=0; i<50; ++i) current_selection.push_back(scores[i].second);
        }

        auto temp_points = build_tour_points(current_selection, all_orders);
        auto temp_tour = build_greedy_tour(temp_points);
        optimize_tour_2opt(temp_tour, temp_points, timer, TIME_LIMIT / 2);
        long long current_cost = calculate_tour_cost(temp_tour, temp_points);

        if (min_cost == -1 || current_cost < min_cost) {
            min_cost = current_cost;
            best_selection = current_selection;
        }
    }
    
    std::vector<int> current_selection = best_selection;
    auto current_points = build_tour_points(current_selection, all_orders);
    auto current_tour = build_greedy_tour(current_points);
    optimize_tour_2opt(current_tour, current_points, timer, TIME_LIMIT);
    long long current_cost = calculate_tour_cost(current_tour, current_points);

    min_cost = current_cost;
    std::vector<int> best_tour = current_tour;

    double start_temp = 2000, end_temp = 1;
    
    while(timer.elapsed_ms() < TIME_LIMIT) {
        long long elapsed_time = timer.elapsed_ms();
        double temp = start_temp + (end_temp - start_temp) * elapsed_time / TIME_LIMIT;
        
        std::uniform_int_distribution<> dis_in(0, 49);
        std::uniform_int_distribution<> dis_out(0, 999);
        
        int idx_in = dis_in(rng);
        
        int order_in_id;
        bool is_in_selection;
        do {
            order_in_id = dis_out(rng) + 1;
            is_in_selection = false;
            for(int id : current_selection) if(id == order_in_id) is_in_selection = true;
        } while (is_in_selection);

        std::vector<int> next_selection = current_selection;
        next_selection[idx_in] = order_in_id;

        auto next_points = build_tour_points(next_selection, all_orders);
        auto next_tour = build_greedy_tour(next_points);
        
        long long next_cost = calculate_tour_cost(next_tour, next_points);

        double prob = std::exp((double)(current_cost - next_cost) / temp);

        if (std::uniform_real_distribution<>(0.0, 1.0)(rng) < prob) {
            current_selection = next_selection;
            current_cost = next_cost;
            current_tour = next_tour;
        }

        if (current_cost < min_cost) {
            min_cost = current_cost;
            best_selection = current_selection;
            best_tour = current_tour;
        }
    }

    auto final_points = build_tour_points(best_selection, all_orders);
    optimize_tour_2opt(best_tour, final_points, timer, TIME_LIMIT);

    std::cout << best_selection.size();
    for (int id : best_selection) std::cout << " " << id;
    std::cout << std::endl;

    auto output_points = build_tour_points(best_selection, all_orders);
    std::vector<Point> path;
    for(int idx : best_tour) path.push_back(output_points[idx].pos);
    path.push_back(output_points[best_tour[0]].pos);

    std::cout << path.size();
    for (const auto& p : path) std::cout << " " << p.x << " " << p.y;
    std::cout << std::endl;

    return 0;
}