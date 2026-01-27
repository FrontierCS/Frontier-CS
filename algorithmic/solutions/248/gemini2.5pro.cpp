#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <iomanip>

const double INF = 1e18;

struct City {
    int id;
    int x;
    std::vector<int> y_coords;
};

double weight_dist, weight_slope;
std::vector<City> cities;
int M;

struct Point_Simple {
    int x, y;
};

double calculate_edge_cost(Point_Simple p1, Point_Simple p2) {
    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dist = std::sqrt(dx * dx + dy * dy);

    double slope = 0.0;
    if (p2.y > p1.y) {
        if (std::abs(dx) < 1e-9) {
            slope = 1e9; // A large number for vertical climb
        } else {
            slope = (p2.y - p1.y) / std::abs(dx);
        }
    }

    return dist * weight_dist + slope * weight_slope;
}

struct Solution {
    double cost;
    std::vector<int> point_indices;
};

Solution calculate_tour_cost(const std::vector<int>& city_order) {
    int num_cities = city_order.size();
    if (num_cities < 2) return {0.0, {}};

    double min_total_cost = INF;
    std::vector<int> best_point_indices(num_cities);

    int start_city_idx = city_order[0];
    const auto& start_city = cities[start_city_idx];

    for (int start_point_idx = 0; start_point_idx < start_city.y_coords.size(); ++start_point_idx) {
        std::vector<std::vector<double>> dp(num_cities, std::vector<double>(21, INF));
        std::vector<std::vector<int>> parent(num_cities, std::vector<int>(21, -1));
        
        Point_Simple p_start = {start_city.x, start_city.y_coords[start_point_idx]};

        int city1_idx = city_order[1];
        const auto& city1 = cities[city1_idx];
        for (int j = 0; j < city1.y_coords.size(); ++j) {
            Point_Simple p_city1 = {city1.x, city1.y_coords[j]};
            dp[1][j] = calculate_edge_cost(p_start, p_city1);
            parent[1][j] = start_point_idx;
        }

        for (int i = 2; i < num_cities; ++i) {
            int prev_city_idx = city_order[i - 1];
            int curr_city_idx = city_order[i];
            const auto& prev_city = cities[prev_city_idx];
            const auto& curr_city = cities[curr_city_idx];

            for (int j = 0; j < curr_city.y_coords.size(); ++j) {
                Point_Simple p_curr = {curr_city.x, curr_city.y_coords[j]};
                double min_cost_to_curr = INF;
                int best_parent_k = -1;
                for (int k = 0; k < prev_city.y_coords.size(); ++k) {
                    Point_Simple p_prev = {prev_city.x, prev_city.y_coords[k]};
                    double new_cost = dp[i-1][k] + calculate_edge_cost(p_prev, p_curr);
                    if (new_cost < min_cost_to_curr) {
                        min_cost_to_curr = new_cost;
                        best_parent_k = k;
                    }
                }
                dp[i][j] = min_cost_to_curr;
                parent[i][j] = best_parent_k;
            }
        }

        double current_min_cost = INF;
        int best_last_point_idx = -1;
        int last_city_idx = city_order[num_cities - 1];
        const auto& last_city = cities[last_city_idx];

        for (int j = 0; j < last_city.y_coords.size(); ++j) {
            Point_Simple p_last = {last_city.x, last_city.y_coords[j]};
            double total_cost = dp[num_cities - 1][j] + calculate_edge_cost(p_last, p_start);
            if (total_cost < current_min_cost) {
                current_min_cost = total_cost;
                best_last_point_idx = j;
            }
        }
        
        if (current_min_cost < min_total_cost) {
            min_total_cost = current_min_cost;
            
            std::vector<int> current_point_indices(num_cities);
            current_point_indices[num_cities - 1] = best_last_point_idx;
            for (int i = num_cities - 1; i >= 1; --i) {
                current_point_indices[i-1] = parent[i][current_point_indices[i]];
            }
            best_point_indices = current_point_indices;
        }
    }
    
    return {min_total_cost, best_point_indices};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    double base_score;
    std::cin >> base_score;

    std::cin >> M;
    cities.resize(M);
    std::vector<std::pair<int, int>> city_x_coords(M);

    for (int i = 0; i < M; ++i) {
        cities[i].id = i + 1;
        int n;
        std::cin >> n >> cities[i].x;
        city_x_coords[i] = {cities[i].x, i};
        cities[i].y_coords.resize(n);
        for (int j = 0; j < n; ++j) {
            std::cin >> cities[i].y_coords[j];
        }
    }

    std::cin >> weight_dist >> weight_slope;

    std::sort(city_x_coords.begin(), city_x_coords.end());
    std::vector<int> current_city_order(M);
    for (int i = 0; i < M; ++i) {
        current_city_order[i] = city_x_coords[i].second;
    }

    Solution best_solution = calculate_tour_cost(current_city_order);
    std::vector<int> best_city_order = current_city_order;
    Solution current_solution = best_solution;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    double T = std::max(1.0, best_solution.cost / 10.0 * (M/200.0 + 0.5));
    double alpha = 0.9995;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_sec = 14.8;
    
    while(true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > time_limit_sec) {
            break;
        }
        
        std::vector<int> next_city_order = current_city_order;
        
        std::uniform_int_distribution<int> dist(0, M - 1);
        int i = dist(rng);
        int j = dist(rng);
        if (i == j) continue;
        if (i > j) std::swap(i, j);

        std::reverse(next_city_order.begin() + i, next_city_order.begin() + j + 1);

        Solution next_solution = calculate_tour_cost(next_city_order);

        double delta = next_solution.cost - current_solution.cost;
        std::uniform_real_distribution<double> unif(0, 1);

        if (delta < 0 || (T > 1e-9 && unif(rng) < std::exp(-delta / T))) {
            current_solution = next_solution;
            current_city_order = next_city_order;
        }
        
        if (current_solution.cost < best_solution.cost) {
            best_solution = current_solution;
            best_city_order = current_city_order;
        }
        
        T *= alpha;
    }

    std::vector<std::pair<int, int>> final_tour(M);
    for (int i = 0; i < M; ++i) {
        int city_idx = best_city_order[i];
        int point_idx = best_solution.point_indices[i];
        final_tour[i] = {cities[city_idx].id, point_idx + 1};
    }

    for (int i = 0; i < M; ++i) {
        std::cout << "(" << final_tour[i].first << "," << final_tour[i].second << ")";
        if (i < M - 1) {
            std::cout << "@";
        }
    }
    std::cout << std::endl;

    return 0;
}