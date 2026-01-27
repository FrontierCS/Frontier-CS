#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iomanip>
#include <chrono>
#include <random>

// Structure to hold point information
struct Point {
    int id;       // Global unique ID for the point
    int city_id;  // 0-indexed city ID
    int lp_idx;   // 0-indexed landing point index within its city
    int x, y;
};

// Global variables for easy access in functions
double D_in, S_in;
const double K = 0.6;
std::vector<Point> all_points;
std::vector<std::vector<int>> city_to_points_map; // city_id -> list of global point IDs
std::vector<std::vector<double>> cost_matrix;
int M;

// Calculates Euclidean distance between two points
double dist(const Point& p1, const Point& p2) {
    return std::sqrt(std::pow(static_cast<double>(p1.x) - p2.x, 2) + std::pow(static_cast<double>(p1.y) - p2.y, 2));
}

// Calculates climbing slope from p1 to p2
double slope(const Point& p1, const Point& p2) {
    if (p1.y >= p2.y) return 0.0;
    double horiz_dist = std::abs(static_cast<double>(p1.x) - p2.x);
    if (horiz_dist < 1e-9) return 1e18; // Treat vertical climbing as extremely high cost
    return (static_cast<double>(p2.y) - p1.y) / horiz_dist;
}

// Calculates the combined cost of an edge
double edge_cost(const Point& p1, const Point& p2) {
    if (p1.city_id == p2.city_id) return 1e18; // Prohibit travel between points in the same city
    return (1.0 - K) / D_in * dist(p1, p2) + K / S_in * slope(p1, p2);
}

// Represents a complete solution
struct Solution {
    std::vector<int> tour;       // Permutation of city IDs (0 to M-1)
    std::vector<int> choices;    // choices[city_id] = global_point_id
    double cost;
};

// Calculates the total cost of a given solution
double calculate_total_cost(const std::vector<int>& tour, const std::vector<int>& choices) {
    double total = 0;
    for (int i = 0; i < M; ++i) {
        int u_city_idx = tour[i];
        int v_city_idx = tour[(i + 1) % M];
        int p1_id = choices[u_city_idx];
        int p2_id = choices[v_city_idx];
        total += cost_matrix[p1_id][p2_id];
    }
    return total;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cout << std::fixed << std::setprecision(10);

    double base;
    std::cin >> base >> M;

    std::vector<std::pair<int, std::vector<int>>> cities_data(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        std::cin >> n >> x;
        cities_data[i].first = x;
        cities_data[i].second.resize(n);
        for (int j = 0; j < n; ++j) {
            std::cin >> cities_data[i].second[j];
        }
    }
    std::cin >> D_in >> S_in;

    int current_point_id = 0;
    city_to_points_map.resize(M);
    for (int i = 0; i < M; ++i) {
        int x = cities_data[i].first;
        for (size_t j = 0; j < cities_data[i].second.size(); ++j) {
            int y = cities_data[i].second[j];
            all_points.push_back({current_point_id, i, static_cast<int>(j), x, y});
            city_to_points_map[i].push_back(current_point_id);
            current_point_id++;
        }
    }

    int total_points = all_points.size();
    cost_matrix.resize(total_points, std::vector<double>(total_points));
    for (int i = 0; i < total_points; ++i) {
        for (int j = 0; j < total_points; ++j) {
            cost_matrix[i][j] = edge_cost(all_points[i], all_points[j]);
        }
    }

    Solution current_sol;
    current_sol.choices.resize(M);
    
    // Initial choices: lowest Y-coordinate landing point for each city
    for(int i = 0; i < M; ++i) {
        int best_pt_id = -1;
        int min_y = 20000;
        for (int pt_id : city_to_points_map[i]) {
            if (all_points[pt_id].y < min_y) {
                min_y = all_points[pt_id].y;
                best_pt_id = pt_id;
            }
        }
        current_sol.choices[i] = best_pt_id;
    }

    // Initial tour: Cheapest Insertion heuristic
    std::vector<int> initial_tour;
    std::vector<bool> in_tour(M, false);
    initial_tour.push_back(0);
    in_tour[0] = true;
    
    if (M > 1) {
        int best_neighbor = -1;
        double min_cost = 1e18;
        for (int i = 1; i < M; ++i) {
            double c = cost_matrix[current_sol.choices[0]][current_sol.choices[i]];
            if (c < min_cost) {
                min_cost = c;
                best_neighbor = i;
            }
        }
        initial_tour.push_back(best_neighbor);
        in_tour[best_neighbor] = true;
    }

    for (int k = 2; k < M; ++k) {
        int best_city_to_insert = -1;
        int best_pos = -1;
        double min_insertion_cost = 1e18;

        for (int city_idx = 0; city_idx < M; ++city_idx) {
            if (!in_tour[city_idx]) {
                int p_k_id = current_sol.choices[city_idx];
                for (size_t i = 0; i < initial_tour.size(); ++i) {
                    int p_i_id = current_sol.choices[initial_tour[i]];
                    int p_j_id = current_sol.choices[initial_tour[(i + 1) % initial_tour.size()]];
                    double insertion_cost = cost_matrix[p_i_id][p_k_id] + cost_matrix[p_k_id][p_j_id] - cost_matrix[p_i_id][p_j_id];
                    if (insertion_cost < min_insertion_cost) {
                        min_insertion_cost = insertion_cost;
                        best_city_to_insert = city_idx;
                        best_pos = i;
                    }
                }
            }
        }
        initial_tour.insert(initial_tour.begin() + best_pos + 1, best_city_to_insert);
        in_tour[best_city_to_insert] = true;
    }
    current_sol.tour = initial_tour;
    current_sol.cost = calculate_total_cost(current_sol.tour, current_sol.choices);

    Solution best_sol = current_sol;

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_sec = 14.9;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_real_distribution<double> unif_dist(0.0, 1.0);
    
    double T_initial = current_sol.cost * 0.1;
    double T_final = 1e-9;
    
    std::vector<int> city_to_tour_pos(M);
    for (int i = 0; i < M; ++i) {
        city_to_tour_pos[current_sol.tour[i]] = i;
    }
    
    while(true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > time_limit_sec) break;
        
        double T = T_initial * std::pow(T_final / T_initial, elapsed.count() / time_limit_sec);

        double move_type = unif_dist(rng);
        
        std::uniform_int_distribution<int> city_dist(0, M - 1);

        if (move_type < 0.5) { // Change landing point
            int c_idx = city_dist(rng);
            if (city_to_points_map[c_idx].size() <= 1) continue;

            std::uniform_int_distribution<int> lp_dist(0, city_to_points_map[c_idx].size() - 1);
            int new_lp_local_idx = lp_dist(rng);
            int new_pt_id = city_to_points_map[c_idx][new_lp_local_idx];
            int old_pt_id = current_sol.choices[c_idx];
            if (new_pt_id == old_pt_id) continue;

            int tour_pos = city_to_tour_pos[c_idx];
            int prev_c_idx = current_sol.tour[(tour_pos - 1 + M) % M];
            int next_c_idx = current_sol.tour[(tour_pos + 1) % M];
            int prev_pt_id = current_sol.choices[prev_c_idx];
            int next_pt_id = current_sol.choices[next_c_idx];

            double delta_cost = (cost_matrix[prev_pt_id][new_pt_id] + cost_matrix[new_pt_id][next_pt_id]) - 
                                (cost_matrix[prev_pt_id][old_pt_id] + cost_matrix[old_pt_id][next_pt_id]);
            
            if (delta_cost < 0 || unif_dist(rng) < std::exp(-delta_cost / T)) {
                current_sol.choices[c_idx] = new_pt_id;
                current_sol.cost += delta_cost;
                if (current_sol.cost < best_sol.cost) {
                    best_sol = current_sol;
                }
            }
        } else { // Swap two cities in tour
            if (M <= 1) continue;
            int i = city_dist(rng);
            int j = city_dist(rng);
            if (i == j) continue;
            
            int c_i = current_sol.tour[i];
            int c_j = current_sol.tour[j];
            int p_i_id = current_sol.choices[c_i];
            int p_j_id = current_sol.choices[c_j];
            
            double delta_cost;
            if ((i + 1) % M == j || (j + 1) % M == i) { // Adjacent
                if ((j + 1) % M == i) std::swap(i,j);
                int c_prev = current_sol.tour[(i - 1 + M) % M];
                int c_next = current_sol.tour[(j + 1) % M];
                int p_prev_id = current_sol.choices[c_prev];
                int p_next_id = current_sol.choices[c_next];
                delta_cost = (cost_matrix[p_prev_id][p_j_id] + cost_matrix[p_j_id][p_i_id] + cost_matrix[p_i_id][p_next_id]) -
                             (cost_matrix[p_prev_id][p_i_id] + cost_matrix[p_i_id][p_j_id] + cost_matrix[p_j_id][p_next_id]);
            } else { // Not adjacent
                int c_i_prev = current_sol.tour[(i - 1 + M) % M];
                int c_i_next = current_sol.tour[(i + 1) % M];
                int c_j_prev = current_sol.tour[(j - 1 + M) % M];
                int c_j_next = current_sol.tour[(j + 1) % M];
                int p_i_prev_id = current_sol.choices[c_i_prev];
                int p_i_next_id = current_sol.choices[c_i_next];
                int p_j_prev_id = current_sol.choices[c_j_prev];
                int p_j_next_id = current_sol.choices[c_j_next];
                
                double old_cost = cost_matrix[p_i_prev_id][p_i_id] + cost_matrix[p_i_id][p_i_next_id] +
                                  cost_matrix[p_j_prev_id][p_j_id] + cost_matrix[p_j_id][p_j_next_id];
                double new_cost = cost_matrix[p_i_prev_id][p_j_id] + cost_matrix[p_j_id][p_i_next_id] +
                                  cost_matrix[p_j_prev_id][p_i_id] + cost_matrix[p_i_id][p_j_next_id];
                delta_cost = new_cost - old_cost;
            }
            
            if (delta_cost < 0 || unif_dist(rng) < std::exp(-delta_cost / T)) {
                std::swap(current_sol.tour[i], current_sol.tour[j]);
                city_to_tour_pos[c_i] = j;
                city_to_tour_pos[c_j] = i;
                current_sol.cost += delta_cost;
                if (current_sol.cost < best_sol.cost) {
                    best_sol = current_sol;
                }
            }
        }
    }
    
    for (int i = 0; i < M; ++i) {
        int city_idx = best_sol.tour[i];
        int point_id = best_sol.choices[city_idx];
        std::cout << "(" << all_points[point_id].city_id + 1 << "," << all_points[point_id].lp_idx + 1 << ")";
        if (i < M - 1) {
            std::cout << "@";
        }
    }
    std::cout << std::endl;

    return 0;
}