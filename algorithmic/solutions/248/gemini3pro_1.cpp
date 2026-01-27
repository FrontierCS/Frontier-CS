#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <ctime>

using namespace std;

// Data structures
struct Point {
    int id; // 1-based index in the city
    int x, y;
};

struct City {
    int id; // 1-based city ID from input order
    int x;
    vector<Point> points;
};

// Global variables
int M;
vector<City> cities;
double D_param, S_param;
double K = 0.6;
double base_cost;
double W_d, W_s;

struct Solution {
    vector<int> perm; // Order of city indices (0 to M-1)
    vector<int> sel;  // Selected point index for each city (0 to n-1)
    double cost;
};

// Helper functions for cost calculation
inline double get_dist(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    return std::sqrt(dx*dx + dy*dy);
}

inline double get_slope_cost(const Point& a, const Point& b) {
    if (b.y <= a.y) return 0.0;
    double h_diff = std::abs(a.x - b.x);
    if (h_diff < 1e-9) return 1e9; // Penalize vertical ascent with same x
    return (double)(b.y - a.y) / h_diff;
}

inline double get_edge_cost(const Point& a, const Point& b) {
    return W_d * get_dist(a, b) + W_s * get_slope_cost(a, b);
}

double calculate_total_cost(const vector<int>& perm, const vector<int>& sel) {
    double total = 0;
    for (int i = 0; i < M; ++i) {
        int u_idx = perm[i];
        int v_idx = perm[(i + 1) % M];
        const Point& u = cities[u_idx].points[sel[u_idx]];
        const Point& v = cities[v_idx].points[sel[v_idx]];
        total += get_edge_cost(u, v);
    }
    return total;
}

mt19937 rng(1337);

// Dynamic Programming to select optimal points for a fixed city permutation
// Complexity: O(M * N^2) per call.
double optimize_points(const vector<int>& perm, vector<int>& sel) {
    int start_city_idx = perm[0];
    int n_start = cities[start_city_idx].points.size();
    
    double best_global_cost = 1e18;
    vector<int> best_sel = sel;
    
    // DP tables reused to save allocation time
    static vector<vector<double>> dp(M, vector<double>(20));
    static vector<vector<int>> parent(M, vector<int>(20));

    // We must fix the starting point of the tour to handle the cycle constraint.
    // Iterate over all possible starting points of the first city in the permutation.
    for (int s = 0; s < n_start; ++s) {
        // Initialize DP table for this start point
        for (int j = 0; j < cities[start_city_idx].points.size(); ++j) dp[0][j] = 1e18;
        dp[0][s] = 0;
        
        // Forward pass
        for (int i = 0; i < M - 1; ++i) {
            int u = perm[i];
            int v = perm[i+1];
            int n_u = cities[u].points.size();
            int n_v = cities[v].points.size();
            
            for(int j=0; j<n_v; ++j) dp[i+1][j] = 1e18;

            for (int j = 0; j < n_u; ++j) {
                if (dp[i][j] > 1e17) continue;
                
                const Point& p_u = cities[u].points[j];
                for (int k = 0; k < n_v; ++k) {
                    const Point& p_v = cities[v].points[k];
                    double cost = get_edge_cost(p_u, p_v);
                    if (dp[i][j] + cost < dp[i+1][k]) {
                        dp[i+1][k] = dp[i][j] + cost;
                        parent[i+1][k] = j; // store predecessor index
                    }
                }
            }
        }
        
        // Closing the cycle
        int last_city = perm[M-1];
        int n_last = cities[last_city].points.size();
        const Point& start_pt = cities[start_city_idx].points[s];
        
        for (int k = 0; k < n_last; ++k) {
            if (dp[M-1][k] > 1e17) continue;
            const Point& end_pt = cities[last_city].points[k];
            double closing_cost = get_edge_cost(end_pt, start_pt);
            double total = dp[M-1][k] + closing_cost;
            
            if (total < best_global_cost) {
                best_global_cost = total;
                // Reconstruct the best selection
                best_sel[perm[0]] = s;
                int curr = k;
                for (int i = M - 1; i > 0; --i) {
                    best_sel[perm[i]] = curr;
                    curr = parent[i][curr];
                }
            }
        }
    }
    
    sel = best_sel;
    return best_global_cost;
}

// Greedy initialization for TSP based on city centers
void greedy_init(Solution& sol) {
    vector<bool> visited(M, false);
    sol.perm.clear();
    sol.perm.reserve(M);
    
    // Pick a random start city
    int start_node = uniform_int_distribution<int>(0, M-1)(rng);
    int current = start_node;
    visited[current] = true;
    sol.perm.push_back(current);
    
    for(int i=0; i<M-1; ++i) {
        int best_next = -1;
        double min_d = 1e18;
        
        // Calculate approx center of current city
        double cur_x = cities[current].x;
        double cur_y = 0;
        for(auto& p : cities[current].points) cur_y += p.y;
        cur_y /= cities[current].points.size();
        
        for(int next=0; next<M; ++next) {
            if(!visited[next]) {
                double nxt_x = cities[next].x;
                double nxt_y = 0;
                for(auto& p : cities[next].points) nxt_y += p.y;
                nxt_y /= cities[next].points.size();
                
                double d = (cur_x - nxt_x)*(cur_x - nxt_x) + (cur_y - nxt_y)*(cur_y - nxt_y);
                if(d < min_d) {
                    min_d = d;
                    best_next = next;
                }
            }
        }
        visited[best_next] = true;
        sol.perm.push_back(best_next);
        current = best_next;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> base_cost)) return 0;
    cin >> M;
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        cities[i].id = i + 1;
        int n;
        cin >> n >> cities[i].x;
        cities[i].points.resize(n);
        for (int j = 0; j < n; ++j) {
            cities[i].points[j].id = j + 1;
            cities[i].points[j].x = cities[i].x;
            cin >> cities[i].points[j].y;
        }
    }
    cin >> D_param >> S_param;

    // Weight coefficients
    W_d = (1.0 - K) / D_param;
    W_s = K / S_param;

    Solution current;
    current.sel.resize(M, 0); // Default selection
    
    // Use greedy heuristic for initial permutation
    greedy_init(current);
    // Optimize points for this permutation
    current.cost = optimize_points(current.perm, current.sel);

    Solution best = current;

    // Simulated Annealing
    double temp = 10.0; 
    double cooling = 0.99995;
    clock_t start_time = clock();
    double time_limit = 14.5; 

    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if (elapsed > time_limit) break;
            if (best.cost <= base_cost) break; // Reached target quality
        }

        int move_type;
        uniform_real_distribution<double> rdist(0.0, 1.0);
        double r = rdist(rng);
        
        // Probability of moves
        // 0.1% DP polish, 30% Change Point, 35% 2-opt, 34.9% Swap
        if (r < 0.001) move_type = 4;
        else if (r < 0.3) move_type = 3;
        else if (r < 0.65) move_type = 1;
        else move_type = 0;
        
        Solution next_sol = current;
        
        if (move_type == 0) { // Swap two cities
            int i = uniform_int_distribution<int>(0, M - 1)(rng);
            int j = uniform_int_distribution<int>(0, M - 1)(rng);
            if (i == j) continue;
            swap(next_sol.perm[i], next_sol.perm[j]);
            next_sol.cost = calculate_total_cost(next_sol.perm, next_sol.sel);
        }
        else if (move_type == 1) { // 2-opt (Reverse segment)
            int i = uniform_int_distribution<int>(0, M - 1)(rng);
            int j = uniform_int_distribution<int>(0, M - 1)(rng);
            if (abs(i - j) < 2) continue;
            if (i > j) swap(i, j);
            reverse(next_sol.perm.begin() + i, next_sol.perm.begin() + j + 1);
            next_sol.cost = calculate_total_cost(next_sol.perm, next_sol.sel);
        }
        else if (move_type == 3) { // Change landing point in a city
            int c_idx = uniform_int_distribution<int>(0, M - 1)(rng);
            int city_id = next_sol.perm[c_idx];
            int num_pts = cities[city_id].points.size();
            if (num_pts <= 1) continue;
            
            int new_pt = uniform_int_distribution<int>(0, num_pts - 1)(rng);
            if (new_pt == next_sol.sel[city_id]) new_pt = (new_pt + 1) % num_pts;
            
            next_sol.sel[city_id] = new_pt;
            next_sol.cost = calculate_total_cost(next_sol.perm, next_sol.sel);
        }
        else if (move_type == 4) { // Full DP Optimization
            next_sol.cost = optimize_points(next_sol.perm, next_sol.sel);
        }
        
        // Metropolis criterion
        double delta = next_sol.cost - current.cost;
        if (delta < 0 || exp(-delta / temp) > rdist(rng)) {
            current = next_sol;
            if (current.cost < best.cost) {
                best = current;
                // Whenever we find a structural improvement, optimize points
                if (move_type != 4) {
                    double polished = optimize_points(best.perm, best.sel);
                    best.cost = polished;
                    current = best; // Sync current with polished best
                }
            }
        }
        
        temp *= cooling;
        if (temp < 1e-4) temp = 1e-4; 
    }
    
    // Final Polish
    optimize_points(best.perm, best.sel);
    
    // Output
    for (int i = 0; i < M; ++i) {
        int c_idx = best.perm[i];
        int p_idx = best.sel[c_idx];
        cout << "(" << cities[c_idx].id << "," << cities[c_idx].points[p_idx].id << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;

    return 0;
}