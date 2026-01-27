#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

// Constants and global variables
const double K = 0.6;
double D_ORIG, S_ORIG;
double D_NORM, S_NORM;

struct Point {
    double x, y;
};

struct City {
    int id;
    double x;
    std::vector<double> ys;
};

std::vector<City> cities;
int M;

// State for Simulated Annealing
std::vector<int> current_tour;
std::vector<int> current_landing_points;
double current_cost;

std::vector<int> best_tour;
std::vector<int> best_landing_points;
double best_cost;

// Random number generator
std::mt19937 rng;

// Helper to get a Point object for a city and landing point index
Point get_point(int city_idx, int lp_idx) {
    return {cities[city_idx].x, cities[city_idx].ys[lp_idx]};
}

// Cost function between two points
double cost_between_points(Point p1, Point p2) {
    if (std::abs(p1.x - p2.x) < 1e-9) {
        return 1e18; // Should not happen between different cities
    }
    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dist = std::sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (p2.y > p1.y) {
        slope = (p2.y - p1.y) / std::abs(dx);
    }
    return D_NORM * dist + S_NORM * slope;
}

// Function to calculate total cost of a tour
double calculate_total_cost(const std::vector<int>& tour, const std::vector<int>& landing_points) {
    double total_cost = 0;
    for (int i = 0; i < M; ++i) {
        int city1_idx = tour[i];
        int city2_idx = tour[(i + 1) % M];
        int lp1_idx = landing_points[city1_idx];
        int lp2_idx = landing_points[city2_idx];
        Point p1 = get_point(city1_idx, lp1_idx);
        Point p2 = get_point(city2_idx, lp2_idx);
        total_cost += cost_between_points(p1, p2);
    }
    return total_cost;
}

// Generate a good initial solution
void generate_initial_solution() {
    // 1. Initial tour by sorting cities based on x-coordinate
    std::vector<int> city_indices(M);
    std::iota(city_indices.begin(), city_indices.end(), 0);
    std::sort(city_indices.begin(), city_indices.end(), [&](int a, int b) {
        return cities[a].x < cities[b].x;
    });
    current_tour = city_indices;

    // 2. Initialize landing points to the first one for each city
    current_landing_points.assign(M, 0);

    // 3. Iteratively refine landing points for the fixed tour
    for (int iter = 0; iter < 10; ++iter) {
        bool changed = false;
        for (int i = 0; i < M; ++i) {
            int city_idx = current_tour[i];
            int prev_city_idx = current_tour[(i - 1 + M) % M];
            int next_city_idx = current_tour[(i + 1) % M];

            int prev_lp_idx = current_landing_points[prev_city_idx];
            int next_lp_idx = current_landing_points[next_city_idx];

            Point p_prev = get_point(prev_city_idx, prev_lp_idx);
            Point p_next = get_point(next_city_idx, next_lp_idx);
            
            int best_lp_for_city = 0;
            double min_cost_contrib = 1e18;

            for (size_t lp_idx = 0; lp_idx < cities[city_idx].ys.size(); ++lp_idx) {
                Point p_curr = get_point(city_idx, lp_idx);
                double cost_contrib = cost_between_points(p_prev, p_curr) + cost_between_points(p_curr, p_next);
                if (cost_contrib < min_cost_contrib) {
                    min_cost_contrib = cost_contrib;
                    best_lp_for_city = lp_idx;
                }
            }
            if (current_landing_points[city_idx] != best_lp_for_city) {
                current_landing_points[city_idx] = best_lp_for_city;
                changed = true;
            }
        }
        if (!changed) break;
    }

    current_cost = calculate_total_cost(current_tour, current_landing_points);
    best_tour = current_tour;
    best_landing_points = current_landing_points;
    best_cost = current_cost;
}

void simulated_annealing() {
    auto start_time = std::chrono::high_resolution_clock::now();
    const double time_limit_ms = 14500.0;

    // SA parameters
    double T_initial = 0.0;
    const double T_min = 1e-9;
    const double alpha = 0.999995;

    // Estimate initial temperature
    double avg_delta = 0;
    int count = 0;
    std::uniform_int_distribution<int> dist(0, M - 1);
    for (int i = 0; i < 100; ++i) {
        int c1_tour_idx = dist(rng);
        int c2_tour_idx = dist(rng);
        if (c1_tour_idx == c2_tour_idx) continue;
        
        std::vector<int> temp_tour = current_tour;
        std::swap(temp_tour[c1_tour_idx], temp_tour[c2_tour_idx]);
        double new_cost_val = calculate_total_cost(temp_tour, current_landing_points);
        if (new_cost_val > current_cost) {
            avg_delta += new_cost_val - current_cost;
            count++;
        }
    }
    if (count > 0) {
        avg_delta /= count;
        T_initial = -avg_delta / std::log(0.5); // For 50% acceptance prob
    } else {
        T_initial = 1.0;
    }
    double T = T_initial;

    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);
    std::uniform_int_distribution<int> city_tour_idx_dist(0, M - 1);

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time).count() > time_limit_ms) {
            break;
        }

        double move_type = prob_dist(rng);

        if (move_type < 0.7) { // 70% 2-opt
            int i = city_tour_idx_dist(rng);
            int j = city_tour_idx_dist(rng);
            if (i == j) continue;
            if (i > j) std::swap(i, j);

            int c_i = current_tour[i];
            int c_i1 = current_tour[i + 1];
            int c_j = current_tour[j];
            int c_j1 = current_tour[(j + 1) % M];

            Point p_i = get_point(c_i, current_landing_points[c_i]);
            Point p_i1 = get_point(c_i1, current_landing_points[c_i1]);
            Point p_j = get_point(c_j, current_landing_points[c_j]);
            Point p_j1 = get_point(c_j1, current_landing_points[c_j1]);
            
            double old_edges_cost = cost_between_points(p_i, p_i1) + cost_between_points(p_j, p_j1);
            double new_edges_cost = cost_between_points(p_i, p_j) + cost_between_points(p_i1, p_j1);
            double delta_cost = new_edges_cost - old_edges_cost;

            if (delta_cost < 0 || prob_dist(rng) < std::exp(-delta_cost / T)) {
                std::reverse(current_tour.begin() + i + 1, current_tour.begin() + j + 1);
                current_cost += delta_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_tour = current_tour;
                }
            }
        } else if (move_type < 0.95) { // 25% change landing point
            int tour_idx = city_tour_idx_dist(rng);
            int city_id = current_tour[tour_idx];
            
            if (cities[city_id].ys.size() <= 1) continue;
            
            std::uniform_int_distribution<int> lp_dist(0, cities[city_id].ys.size() - 1);
            int new_lp_idx = lp_dist(rng);
            int old_lp_idx = current_landing_points[city_id];
            if (new_lp_idx == old_lp_idx) continue;

            int prev_city_id = current_tour[(tour_idx - 1 + M) % M];
            int next_city_id = current_tour[(tour_idx + 1) % M];
            Point p_prev = get_point(prev_city_id, current_landing_points[prev_city_id]);
            Point p_next = get_point(next_city_id, current_landing_points[next_city_id]);
            Point p_old = get_point(city_id, old_lp_idx);
            Point p_new = get_point(city_id, new_lp_idx);

            double old_contrib = cost_between_points(p_prev, p_old) + cost_between_points(p_old, p_next);
            double new_contrib = cost_between_points(p_prev, p_new) + cost_between_points(p_new, p_next);
            double delta_cost = new_contrib - old_contrib;
            
            if (delta_cost < 0 || prob_dist(rng) < std::exp(-delta_cost / T)) {
                current_landing_points[city_id] = new_lp_idx;
                current_cost += delta_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_landing_points = current_landing_points;
                    best_tour = current_tour;
                }
            }
        } else { // 5% swap cities
            int i = city_tour_idx_dist(rng);
            int j = city_tour_idx_dist(rng);
            if (i == j) continue;

            std::vector<int> next_tour = current_tour;
            std::swap(next_tour[i], next_tour[j]);
            double new_total_cost = calculate_total_cost(next_tour, current_landing_points);
            double delta_cost = new_total_cost - current_cost;

            if (delta_cost < 0 || prob_dist(rng) < std::exp(-delta_cost / T)) {
                current_tour = next_tour;
                current_cost = new_total_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_tour = current_tour;
                    best_landing_points = current_landing_points;
                }
            }
        }
        
        if (T > T_min) {
            T *= alpha;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    double base;
    std::cin >> base;
    std::cin >> M;
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        cities[i].id = i + 1;
        int n;
        std::cin >> n >> cities[i].x;
        cities[i].ys.resize(n);
        for (int j = 0; j < n; ++j) {
            std::cin >> cities[i].ys[j];
        }
    }
    std::cin >> D_ORIG >> S_ORIG;

    D_NORM = (1.0 - K) / D_ORIG;
    S_NORM = K / S_ORIG;
    
    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());

    generate_initial_solution();
    simulated_annealing();

    // Output the best solution found
    for (int i = 0; i < M; ++i) {
        int city_idx = best_tour[i];
        int lp_idx = best_landing_points[city_idx];
        std::cout << "(" << cities[city_idx].id << "," << lp_idx + 1 << ")";
        if (i < M - 1) {
            std::cout << "@";
        }
    }
    std::cout << std::endl;

    return 0;
}