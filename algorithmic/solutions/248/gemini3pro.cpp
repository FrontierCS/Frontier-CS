#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <chrono>
#include <limits>

using namespace std;

// Structure to represent a landing point
struct Point {
    int x, y;
    int city_idx; // 0 to M-1
    int local_idx; // 1 to n (as in problem)
    int global_idx; // unique ID for every point across all cities
};

// Structure to represent a city
struct City {
    int id; // 1 to M (as in input)
    vector<Point> points;
};

int M;
vector<City> cities;
vector<Point> all_points;
double base_cost;
double D_norm, S_norm;
double W_d, W_s;

// Precomputed costs between all pairs of points
// cost_matrix[u][v] is cost from global point u to global point v
vector<vector<double>> cost_matrix;

// Precomputed min costs between cities (heuristic for initial tour)
vector<vector<double>> city_min_cost;

// Calculate Euclidean distance
double get_dist(const Point& a, const Point& b) {
    return sqrt(pow(a.x - b.x, 2) + pow(a.y - b.y, 2));
}

// Calculate slope cost
double get_slope_cost(const Point& a, const Point& b) {
    if (b.y <= a.y) return 0.0;
    double dx = std::abs(b.x - a.x);
    if (dx < 1e-5) return 1e9; // Large penalty for purely vertical climb
    return (double)(b.y - a.y) / dx;
}

// Precompute distance and cost matrices
void precompute() {
    int total_points = all_points.size();
    cost_matrix.assign(total_points, vector<double>(total_points));
    
    // Calculate weights based on problem formula
    double k = 0.6;
    W_d = (1.0 - k) / D_norm;
    W_s = k / S_norm;

    for (int i = 0; i < total_points; ++i) {
        for (int j = 0; j < total_points; ++j) {
            if (i == j) {
                cost_matrix[i][j] = 0;
                continue;
            }
            double dist = get_dist(all_points[i], all_points[j]);
            double slope = get_slope_cost(all_points[i], all_points[j]);
            cost_matrix[i][j] = W_d * dist + W_s * slope;
        }
    }

    city_min_cost.assign(M, vector<double>(M, 1e18));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            double min_c = 1e18;
            for (const auto& p1 : cities[i].points) {
                for (const auto& p2 : cities[j].points) {
                    double c = cost_matrix[p1.global_idx][p2.global_idx];
                    if (c < min_c) min_c = c;
                }
            }
            city_min_cost[i][j] = min_c;
        }
    }
}

// DP to find optimal points for a fixed city permutation
// Returns {min_cost, vector_of_local_indices}
pair<double, vector<int>> optimize_points_for_tour(const vector<int>& tour) {
    int c0 = tour[0];
    int n0 = cities[c0].points.size();
    
    double best_total_cost = 1e18;
    vector<int> best_indices(M);

    // Try each point in the first city as the start/end of the cycle
    // Optimization: for M=200, n=20, this is acceptable for infrequent calls (or once at end)
    for (int start_pt_idx = 0; start_pt_idx < n0; ++start_pt_idx) {
        int start_global = cities[c0].points[start_pt_idx].global_idx;
        
        vector<double> dp_prev(1, 0.0); // Cost to current point
        // We only track the current valid path starting from start_pt_idx
        
        // Path parents to reconstruct solution
        vector<vector<int>> path_parents(M); 
        
        // Initialize for first step: c0 -> c1
        int c1 = tour[1];
        int n1 = cities[c1].points.size();
        vector<double> dp_curr(n1);
        path_parents[1].resize(n1);
        
        for(int j=0; j<n1; ++j) {
            int p_global = cities[c1].points[j].global_idx;
            dp_curr[j] = cost_matrix[start_global][p_global];
            path_parents[1][j] = start_pt_idx;
        }
        dp_prev = dp_curr;

        for (int i = 2; i < M; ++i) {
            int curr_c = tour[i];
            int prev_c = tour[i-1];
            int n_curr = cities[curr_c].points.size();
            int n_prev = cities[prev_c].points.size();
            
            dp_curr.assign(n_curr, 1e18);
            path_parents[i].resize(n_curr);
            
            for (int j = 0; j < n_curr; ++j) {
                int curr_global = cities[curr_c].points[j].global_idx;
                for (int k = 0; k < n_prev; ++k) {
                    int prev_global = cities[prev_c].points[k].global_idx;
                    double val = dp_prev[k] + cost_matrix[prev_global][curr_global];
                    if (val < dp_curr[j]) {
                        dp_curr[j] = val;
                        path_parents[i][j] = k;
                    }
                }
            }
            dp_prev = dp_curr;
        }
        
        // Close the loop: tour[M-1] -> tour[0] (fixed start_pt_idx)
        int last_c = tour[M-1];
        int n_last = cities[last_c].points.size();
        
        double min_cycle_cost = 1e18;
        int best_last_idx = -1;
        
        for (int k = 0; k < n_last; ++k) {
            int last_global = cities[last_c].points[k].global_idx;
            double val = dp_prev[k] + cost_matrix[last_global][start_global];
            if (val < min_cycle_cost) {
                min_cycle_cost = val;
                best_last_idx = k;
            }
        }
        
        if (min_cycle_cost < best_total_cost) {
            best_total_cost = min_cycle_cost;
            vector<int> current_indices(M);
            current_indices[0] = start_pt_idx;
            int curr = best_last_idx;
            for (int i = M - 1; i >= 1; --i) {
                current_indices[i] = curr;
                curr = path_parents[i][curr];
            }
            best_indices = current_indices;
        }
    }
    return {best_total_cost, best_indices};
}

// Fast evaluation of current configuration
double evaluate(const vector<int>& tour, const vector<int>& pt_indices) {
    double cost = 0;
    for (int i = 0; i < M; ++i) {
        int u_city = tour[i];
        int v_city = tour[(i + 1) % M];
        int u_pt = cities[u_city].points[pt_indices[i]].global_idx;
        int v_pt = cities[v_city].points[pt_indices[(i + 1) % M]].global_idx;
        cost += cost_matrix[u_pt][v_pt];
    }
    return cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Read input
    cin >> base_cost;
    cin >> M;
    
    int global_id_counter = 0;
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        City city;
        city.id = i + 1;
        for (int j = 0; j < n; ++j) {
            int y;
            cin >> y;
            Point p = {x, y, i, j + 1, global_id_counter++};
            city.points.push_back(p);
            all_points.push_back(p);
        }
        cities.push_back(city);
    }
    cin >> D_norm >> S_norm;
    
    precompute();
    
    // Initial solution: Greedy Nearest Neighbor based on Min City Cost
    vector<int> current_tour(M);
    vector<bool> visited(M, false);
    
    current_tour[0] = 0;
    visited[0] = true;
    for(int i=1; i<M; ++i) {
        int last = current_tour[i-1];
        double best_dist = 1e18;
        int best_next = -1;
        for(int j=0; j<M; ++j) {
            if(!visited[j]) {
                if(city_min_cost[last][j] < best_dist) {
                    best_dist = city_min_cost[last][j];
                    best_next = j;
                }
            }
        }
        current_tour[i] = best_next;
        visited[best_next] = true;
    }
    
    // Initial points optimization
    auto dp_res = optimize_points_for_tour(current_tour);
    double current_cost = dp_res.first;
    vector<int> current_points = dp_res.second;
    
    // Global best tracking
    double best_cost = current_cost;
    vector<int> best_tour = current_tour;
    vector<int> best_points = current_points;
    
    // SA Setup
    mt19937 rng(1337);
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 14.5; // seconds
    
    double T_start = 100.0; 
    double T_end = 0.001;
    double T = T_start;
    
    int iter = 0;
    while(true) {
        iter++;
        if (iter % 1000 == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Periodically sync with full DP to correct point drift
            if (iter % 10000 == 0) {
                 auto res = optimize_points_for_tour(current_tour);
                 if (res.first < current_cost) {
                     current_cost = res.first;
                     current_points = res.second;
                     if (current_cost < best_cost) {
                         best_cost = current_cost;
                         best_tour = current_tour;
                         best_points = current_points;
                     }
                 }
            }
        }
        
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        double progress = elapsed.count() / time_limit;
        if (progress >= 1.0) break;
        T = T_start * pow(T_end / T_start, progress);

        int move_type = rng() % 100;
        
        if (move_type < 20) { // Swap Cities
            int i = rng() % M;
            int j = rng() % M;
            if (i == j) continue;
            
            swap(current_tour[i], current_tour[j]);
            swap(current_points[i], current_points[j]); 
            
            double new_cost = evaluate(current_tour, current_points);
            double delta = new_cost - current_cost;
            
            if (delta < 0 || exp(-delta / T) > (double)rng() / rng.max()) {
                current_cost = new_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_tour = current_tour;
                    best_points = current_points;
                }
            } else {
                // Revert
                swap(current_points[i], current_points[j]);
                swap(current_tour[i], current_tour[j]);
            }
        } else if (move_type < 50) { // 2-Opt Cities
            int i = rng() % M;
            int j = rng() % M;
            if (i == j) continue;
            int a = min(i, j);
            int b = max(i, j);
            
            reverse(current_tour.begin() + a, current_tour.begin() + b + 1);
            reverse(current_points.begin() + a, current_points.begin() + b + 1);
            
            double new_cost = evaluate(current_tour, current_points);
            double delta = new_cost - current_cost;
            
            if (delta < 0 || exp(-delta / T) > (double)rng() / rng.max()) {
                current_cost = new_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_tour = current_tour;
                    best_points = current_points;
                }
            } else {
                reverse(current_tour.begin() + a, current_tour.begin() + b + 1);
                reverse(current_points.begin() + a, current_points.begin() + b + 1);
            }
        } else if (move_type < 70) { // Relocate (Insert) City
            int i = rng() % M;
            int j = rng() % M;
            if (i == j) continue;
            
            int city_val = current_tour[i];
            int pt_val = current_points[i];
            
            vector<int> next_tour = current_tour;
            vector<int> next_points = current_points;
            
            next_tour.erase(next_tour.begin() + i);
            next_points.erase(next_points.begin() + i);
            
            next_tour.insert(next_tour.begin() + j, city_val);
            next_points.insert(next_points.begin() + j, pt_val);
            
            double new_cost = evaluate(next_tour, next_points);
            double delta = new_cost - current_cost;
            
            if (delta < 0 || exp(-delta / T) > (double)rng() / rng.max()) {
                current_tour = next_tour;
                current_points = next_points;
                current_cost = new_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_tour = current_tour;
                    best_points = current_points;
                }
            }
        } else { // Change Point
            int idx = rng() % M;
            int c_idx = current_tour[idx];
            int n_pts = cities[c_idx].points.size();
            if (n_pts > 1) {
                int old_pt = current_points[idx];
                int new_pt = rng() % n_pts;
                if (new_pt == old_pt) new_pt = (new_pt + 1) % n_pts;
                
                int prev_idx = (idx - 1 + M) % M;
                int next_idx = (idx + 1) % M;
                
                int p_prev = cities[current_tour[prev_idx]].points[current_points[prev_idx]].global_idx;
                int p_next = cities[current_tour[next_idx]].points[current_points[next_idx]].global_idx;
                
                int p_old_global = cities[c_idx].points[old_pt].global_idx;
                int p_new_global = cities[c_idx].points[new_pt].global_idx;
                
                double old_seg_cost = cost_matrix[p_prev][p_old_global] + cost_matrix[p_old_global][p_next];
                double new_seg_cost = cost_matrix[p_prev][p_new_global] + cost_matrix[p_new_global][p_next];
                
                double delta = new_seg_cost - old_seg_cost;
                
                if (delta < 0 || exp(-delta / T) > (double)rng() / rng.max()) {
                    current_points[idx] = new_pt;
                    current_cost += delta;
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_tour = current_tour;
                        best_points = current_points;
                    }
                }
            }
        }
    }
    
    // Final polish with full DP
    auto final_res = optimize_points_for_tour(best_tour);
    if (final_res.first < best_cost) {
        best_cost = final_res.first;
        best_points = final_res.second;
    }
    
    // Output
    for (int i = 0; i < M; ++i) {
        if (i > 0) cout << "@";
        cout << "(" << cities[best_tour[i]].id << "," << cities[best_tour[i]].points[best_points[i]].local_idx << ")";
    }
    cout << endl;

    return 0;
}