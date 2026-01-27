#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <iomanip>

using namespace std;

// Constants and Global Variables
const double K = 0.6;
double BaseCost;
int M;
double D_norm, S_norm;
double W_D, W_S;

struct LandingPoint {
    int id; // 1-based index within city
    int x, y;
    int global_id; // Unique ID across all points
};

struct City {
    int id; // 1-based city id
    int x;
    vector<LandingPoint> points;
};

vector<City> cities;
int total_points = 0;

// Adjacency matrix for costs between all landing points
// cost_matrix[u][v] stores the weighted cost from global point u to global point v
vector<vector<double>> cost_matrix;

void precompute_costs() {
    cost_matrix.assign(total_points, vector<double>(total_points));
    vector<pair<int, int>> all_coords(total_points);
    
    // Map global ID to coordinates
    for (const auto& c : cities) {
        for (const auto& p : c.points) {
            all_coords[p.global_id] = {c.x, p.y};
        }
    }

    for (int i = 0; i < total_points; ++i) {
        for (int j = 0; j < total_points; ++j) {
            if (i == j) {
                cost_matrix[i][j] = 0;
                continue;
            }
            double dx = all_coords[i].first - all_coords[j].first;
            double dy = all_coords[i].second - all_coords[j].second;
            double dist = sqrt(dx*dx + dy*dy);
            
            double slope = 0;
            double abs_dx = abs(dx);
            // Protect against division by zero; treat as very steep if dx is effectively 0
            if (abs_dx < 1e-9) abs_dx = 1e-9; 
            
            // Energy consumption only if climbing
            if (all_coords[j].second > all_coords[i].second) {
                slope = (all_coords[j].second - all_coords[i].second) / abs_dx;
            } else {
                slope = 0;
            }
            
            cost_matrix[i][j] = W_D * dist + W_S * slope;
        }
    }
}

struct Solution {
    vector<int> city_perm; // indices of cities in 'cities' vector (0 to M-1)
    vector<int> point_indices; // index of selected point within the city (0 to n-1)
    double cost;
};

// Optimizes the selection of landing points for a fixed city permutation using DP
// Returns the optimal cost and updates sol.point_indices and sol.cost
double optimize_points(Solution& sol) {
    int first_city_idx = sol.city_perm[0];
    const auto& first_city_pts = cities[first_city_idx].points;
    int n_first = first_city_pts.size();
    
    double best_cycle_cost = 1e18;
    
    // DP tables
    // parent[start_point_idx][city_step][current_point_idx]
    static int parent[20][205][20]; 
    // dp[city_step][current_point_idx]
    static double dp[205][20]; 
    
    // Try each landing point of the first city as the start/end of the cycle
    for (int s = 0; s < n_first; ++s) {
        // Initialize DP table
        for (int i = 0; i <= M; ++i) {
            for (int j = 0; j < 20; ++j) {
                dp[i][j] = 1e18;
            }
        }
            
        dp[0][s] = 0;
        
        // Forward pass
        for (int i = 0; i < M - 1; ++i) {
            int curr_c_idx = sol.city_perm[i];
            int next_c_idx = sol.city_perm[i+1];
            const auto& curr_pts = cities[curr_c_idx].points;
            const auto& next_pts = cities[next_c_idx].points;
            
            for (int u = 0; u < curr_pts.size(); ++u) {
                if (dp[i][u] > 1e17) continue;
                
                int u_global = curr_pts[u].global_id;
                
                for (int v = 0; v < next_pts.size(); ++v) {
                    int v_global = next_pts[v].global_id;
                    double new_cost = dp[i][u] + cost_matrix[u_global][v_global];
                    
                    if (new_cost < dp[i+1][v]) {
                        dp[i+1][v] = new_cost;
                        parent[s][i+1][v] = u;
                    }
                }
            }
        }
        
        // Close the loop (return to start point s)
        int last_c_idx = sol.city_perm[M-1];
        const auto& last_pts = cities[last_c_idx].points;
        int first_global = first_city_pts[s].global_id;
        
        for (int u = 0; u < last_pts.size(); ++u) {
             if (dp[M-1][u] > 1e17) continue;
             int u_global = last_pts[u].global_id;
             double total = dp[M-1][u] + cost_matrix[u_global][first_global];
             
             if (total < best_cycle_cost) {
                 best_cycle_cost = total;
                 // Reconstruct path
                 vector<int> path(M);
                 path[M-1] = u;
                 int curr = u;
                 for (int k = M-1; k > 0; --k) {
                     curr = parent[s][k][curr];
                     path[k-1] = curr;
                 }
                 sol.point_indices = path;
             }
        }
    }
    sol.cost = best_cycle_cost;
    return best_cycle_cost;
}

// TSP Local Search (First Improvement)
// Uses Relocate (Insert) and Swap moves
bool tsp_local_search(Solution& sol) {
    // Flatten current tour to global IDs for quick lookup
    vector<int> tour_nodes(M);
    for(int i=0; i<M; ++i) {
        tour_nodes[i] = cities[sol.city_perm[i]].points[sol.point_indices[i]].global_id;
    }
    
    auto get_cost = [&](int u, int v) {
        return cost_matrix[tour_nodes[u]][tour_nodes[v]];
    };
    
    // Relocate Move: Move city at index i to insert before index j
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            int prev_i = (i - 1 + M) % M;
            int next_i = (i + 1) % M;
            int prev_j = (j - 1 + M) % M;
            
            // Check if move is trivial or valid
            if (next_i == j || i == prev_j) continue; 
            
            double delta = 0;
            // Remove edges
            delta -= get_cost(prev_i, i);
            delta -= get_cost(i, next_i);
            delta -= get_cost(prev_j, j);
            
            // Add edges
            delta += get_cost(prev_i, next_i);
            delta += get_cost(prev_j, i);
            delta += get_cost(i, j);
            
            if (delta < -1e-9) {
                // Apply move
                int city_i = sol.city_perm[i];
                int pt_i = sol.point_indices[i];
                
                if (i < j) {
                    sol.city_perm.erase(sol.city_perm.begin() + i);
                    sol.point_indices.erase(sol.point_indices.begin() + i);
                    sol.city_perm.insert(sol.city_perm.begin() + (j - 1), city_i);
                    sol.point_indices.insert(sol.point_indices.begin() + (j - 1), pt_i);
                } else {
                    sol.city_perm.erase(sol.city_perm.begin() + i);
                    sol.point_indices.erase(sol.point_indices.begin() + i);
                    sol.city_perm.insert(sol.city_perm.begin() + j, city_i);
                    sol.point_indices.insert(sol.point_indices.begin() + j, pt_i);
                }
                
                sol.cost += delta;
                return true; 
            }
        }
    }
    
    // Swap Move: Swap cities at index i and j
    for (int i = 0; i < M; ++i) {
        for (int j = i + 1; j < M; ++j) {
            int prev_i = (i - 1 + M) % M;
            int next_i = (i + 1) % M;
            int prev_j = (j - 1 + M) % M;
            int next_j = (j + 1) % M;
            
            double delta = 0;
            
            if (next_i == j) { // adjacent: ... prev_i -> i -> j -> next_j ...
                 delta -= get_cost(prev_i, i);
                 delta -= get_cost(i, j);
                 delta -= get_cost(j, next_j);
                 
                 delta += get_cost(prev_i, j);
                 delta += get_cost(j, i);
                 delta += get_cost(i, next_j);
            } else {
                delta -= get_cost(prev_i, i);
                delta -= get_cost(i, next_i);
                delta -= get_cost(prev_j, j);
                delta -= get_cost(j, next_j);
                
                delta += get_cost(prev_i, j);
                delta += get_cost(j, next_i);
                delta += get_cost(prev_j, i);
                delta += get_cost(i, next_j);
            }
            
            if (delta < -1e-9) {
                swap(sol.city_perm[i], sol.city_perm[j]);
                swap(sol.point_indices[i], sol.point_indices[j]);
                sol.cost += delta;
                return true;
            }
        }
    }
    
    return false;
}

// Double Bridge Perturbation
void perturbation(Solution& sol) {
    if (M < 4) return;
    int pos1 = rand() % (M / 4) + 1;
    int pos2 = pos1 + rand() % (M / 4) + 1;
    int pos3 = pos2 + rand() % (M / 4) + 1;
    
    // Split into 4 segments and reconnect
    vector<int> new_perm, new_pts;
    auto add_seg = [&](int start, int end) {
        for(int i=start; i<=end; ++i) {
            new_perm.push_back(sol.city_perm[i]);
            new_pts.push_back(sol.point_indices[i]);
        }
    };
    
    // Reconnect as A D C B
    add_seg(0, pos1-1);         // A
    add_seg(pos3, M-1);         // D
    add_seg(pos2, pos3-1);      // C
    add_seg(pos1, pos2-1);      // B
    
    sol.city_perm = new_perm;
    sol.point_indices = new_pts;
}

Solution best_sol;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> BaseCost)) return 0;
    cin >> M;
    
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].id = i + 1;
        cities[i].x = x;
        cities[i].points.resize(n);
        for (int j = 0; j < n; ++j) {
            int y;
            cin >> y;
            cities[i].points[j] = {j + 1, x, y, total_points++};
        }
    }
    
    double D_in, S_in;
    cin >> D_in >> S_in;
    D_norm = D_in;
    S_norm = S_in;
    
    W_D = (1.0 - K) / D_norm;
    W_S = K / S_norm;
    
    precompute_costs();
    
    best_sol.cost = 1e18;
    
    auto start_time = chrono::high_resolution_clock::now();
    
    // Initial Solution: Sort by X coordinate
    Solution initial_sol;
    initial_sol.city_perm.resize(M);
    for(int i=0; i<M; ++i) initial_sol.city_perm[i] = i;
    
    sort(initial_sol.city_perm.begin(), initial_sol.city_perm.end(), [&](int a, int b){
        return cities[a].x < cities[b].x;
    });
    
    initial_sol.point_indices.assign(M, 0);
    optimize_points(initial_sol);
    
    if (initial_sol.cost < best_sol.cost) best_sol = initial_sol;
    
    Solution current_sol = initial_sol;
    
    int iter = 0;
    while (true) {
        iter++;
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > 14.5) break;
        
        // Coordinate Descent / Iterated Local Search
        bool improved = true;
        while(improved) {
            improved = false;
            
            // 1. Optimize Points (Cycle DP)
            double old_cost = current_sol.cost;
            optimize_points(current_sol);
            if (current_sol.cost < old_cost - 1e-9) improved = true;
            
            // 2. Optimize Tour (TSP Local Search)
            // Repeat local search until local optimum or timeout
            while (tsp_local_search(current_sol)) {
                improved = true;
                now = chrono::high_resolution_clock::now();
                if ((now - start_time).count() > 14.5) break;
            }
            
            now = chrono::high_resolution_clock::now();
            if ((now - start_time).count() > 14.5) break;
        }
        
        if (current_sol.cost < best_sol.cost) {
            best_sol = current_sol;
        }
        
        // Restart or Perturb
        if (iter % 20 == 0) {
            // Full Restart
            current_sol.city_perm.resize(M);
            for(int i=0; i<M; ++i) current_sol.city_perm[i] = i;
            shuffle(current_sol.city_perm.begin(), current_sol.city_perm.end(), mt19937(rand()));
            current_sol.point_indices.assign(M, 0);
            optimize_points(current_sol);
        } else {
            perturbation(current_sol);
            optimize_points(current_sol);
        }
    }
    
    // Output
    for (int i = 0; i < M; ++i) {
        int c_idx = best_sol.city_perm[i];
        int p_idx = best_sol.point_indices[i];
        cout << "(" << cities[c_idx].id << "," << cities[c_idx].points[p_idx].id << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;

    return 0;
}