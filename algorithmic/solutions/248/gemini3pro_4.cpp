#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>
#include <ctime>

using namespace std;

// Problem constants
const double k_val = 0.6;

struct City {
    int id;
    int n;
    int x;
    vector<int> y;
};

int M;
vector<City> cities;
double base_cost;
double D_in, S_in;
double factor_dist;
double factor_slope;

// Precomputed cost matrix
vector<double> cost_matrix;
vector<int> city_base_idx;
int total_points = 0;

// Helper: Calculate raw cost between two points
double get_dist_raw(const City& c1, int p1, const City& c2, int p2) {
    double dx = (double)c1.x - c2.x;
    double dy = (double)c1.y[p1] - c2.y[p2];
    return sqrt(dx * dx + dy * dy);
}

double get_slope_cost_raw(const City& c1, int p1, const City& c2, int p2) {
    double dy = (double)c2.y[p2] - c1.y[p1];
    if (dy <= 0) return 0.0;
    double dx = std::abs((double)c1.x - c2.x);
    if (dx < 1e-9) return 1e18; // High cost for vertical ascent without horizontal moves (should not happen for distinct cities)
    return dy / dx;
}

double calc_edge_cost_raw(const City& c1, int p1, const City& c2, int p2) {
    double d = get_dist_raw(c1, p1, c2, p2);
    double s = get_slope_cost_raw(c1, p1, c2, p2);
    return factor_dist * d + factor_slope * s;
}

// Fast cost lookup
inline double get_cost(int c1, int p1, int c2, int p2) {
    return cost_matrix[(city_base_idx[c1] + p1) * total_points + (city_base_idx[c2] + p2)];
}

// State
vector<int> current_perm;
vector<int> current_sel;
double current_total_cost;

double calculate_full_cost(const vector<int>& perm, const vector<int>& sel) {
    double cost = 0;
    for (int i = 0; i < M; ++i) {
        cost += get_cost(perm[i], sel[perm[i]], perm[(i + 1) % M], sel[perm[(i + 1) % M]]);
    }
    return cost;
}

// Exact DP to find optimal points for a fixed city permutation
// Returns optimal cost and updates optimal_sel
double optimize_points_exact(const vector<int>& perm, vector<int>& optimal_sel) {
    int first_city = perm[0];
    int n_first = cities[first_city].n;
    
    double best_cycle_cost = 1e18;
    vector<int> best_overall_sel(M);
    
    // Static buffers to avoid reallocation
    static vector<vector<int>> parent(205, vector<int>(25));
    static vector<double> prev_dp(25);
    static vector<double> next_dp(25);
    
    for (int start_pt = 0; start_pt < n_first; ++start_pt) {
        for(int k=0; k<cities[first_city].n; ++k) prev_dp[k] = 1e18;
        prev_dp[start_pt] = 0;
        
        for (int i = 1; i < M; ++i) {
            int u = perm[i-1];
            int v = perm[i];
            int n_u = cities[u].n;
            int n_v = cities[v].n;
            int u_base = city_base_idx[u];
            int v_base = city_base_idx[v];
            
            for(int k=0; k<n_v; ++k) next_dp[k] = 1e18;
            
            for (int pv = 0; pv < n_v; ++pv) {
                double min_val = 1e18;
                int best_prev = -1;
                int v_idx = v_base + pv;
                
                for (int pu = 0; pu < n_u; ++pu) {
                    if (prev_dp[pu] > 1e17) continue;
                    double cost = cost_matrix[(u_base + pu) * total_points + v_idx];
                    double val = prev_dp[pu] + cost;
                    if (val < min_val) {
                        min_val = val;
                        best_prev = pu;
                    }
                }
                next_dp[pv] = min_val;
                parent[i][pv] = best_prev;
            }
            
            for(int k=0; k<n_v; ++k) prev_dp[k] = next_dp[k];
        }
        
        // Close loop
        int u = perm[M-1];
        int v = perm[0];
        int n_u = cities[u].n;
        int u_base = city_base_idx[u];
        int v_target = city_base_idx[v] + start_pt;
        
        double cycle_cost = 1e18;
        int last_pt = -1;
        
        for (int pu = 0; pu < n_u; ++pu) {
            if (prev_dp[pu] > 1e17) continue;
            double cost = cost_matrix[(u_base + pu) * total_points + v_target];
            if (prev_dp[pu] + cost < cycle_cost) {
                cycle_cost = prev_dp[pu] + cost;
                last_pt = pu;
            }
        }
        
        if (cycle_cost < best_cycle_cost) {
            best_cycle_cost = cycle_cost;
            best_overall_sel[0] = start_pt;
            best_overall_sel[M-1] = last_pt;
            int curr = last_pt;
            for (int i = M-1; i > 0; --i) {
                curr = parent[i][curr];
                best_overall_sel[i-1] = curr;
            }
        }
    }
    
    if (best_cycle_cost < 1e17) {
        optimal_sel = best_overall_sel;
        return best_cycle_cost;
    }
    return 1e18;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> base_cost)) return 0;
    cin >> M;
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        cities[i].id = i + 1;
        cin >> cities[i].n >> cities[i].x;
        cities[i].y.resize(cities[i].n);
        for (int j = 0; j < cities[i].n; ++j) {
            cin >> cities[i].y[j];
        }
    }
    cin >> D_in >> S_in;

    factor_dist = (1.0 - k_val) / D_in;
    factor_slope = k_val / S_in;

    // Precompute Cost Matrix
    city_base_idx.resize(M);
    total_points = 0;
    for (int i = 0; i < M; ++i) {
        city_base_idx[i] = total_points;
        total_points += cities[i].n;
    }
    cost_matrix.resize(total_points * total_points);

    for (int i = 0; i < M; ++i) {
        for (int pi = 0; pi < cities[i].n; ++pi) {
            int u = city_base_idx[i] + pi;
            for (int j = 0; j < M; ++j) {
                if (i == j) continue;
                for (int pj = 0; pj < cities[j].n; ++pj) {
                    int v = city_base_idx[j] + pj;
                    cost_matrix[u * total_points + v] = calc_edge_cost_raw(cities[i], pi, cities[j], pj);
                }
            }
        }
    }

    // Initialization
    mt19937 rng(1337);
    current_perm.resize(M);
    for (int i = 0; i < M; ++i) current_perm[i] = i;
    shuffle(current_perm.begin(), current_perm.end(), rng);
    
    current_sel.resize(M, 0);
    // Initial exact optimization
    double exact = optimize_points_exact(current_perm, current_sel);
    current_total_cost = exact;

    vector<int> best_perm = current_perm;
    vector<int> best_sel = current_sel;
    double best_cost = current_total_cost;

    // Simulated Annealing
    double temp = 0.5;
    double cooling_rate = 0.9997;
    double time_limit = 14.8 * CLOCKS_PER_SEC;
    clock_t start_time = clock();
    
    vector<int> next_sel = current_sel; // reuse buffer
    
    while (clock() - start_time < time_limit) {
        if (best_cost <= base_cost) break;

        vector<int> next_perm = current_perm;
        int move_type = rng() % 3;
        int i = rng() % M;
        int j = rng() % M;
        while (i == j) j = rng() % M;

        if (move_type == 0) { // Reverse
            int a = min(i, j);
            int b = max(i, j);
            reverse(next_perm.begin() + a, next_perm.begin() + b + 1);
        } else if (move_type == 1) { // Insert
            int val = next_perm[i];
            next_perm.erase(next_perm.begin() + i);
            next_perm.insert(next_perm.begin() + j, val);
        } else { // Swap
            swap(next_perm[i], next_perm[j]);
        }
        
        // Fast local point optimization (1 pass)
        // We reuse next_sel from previous state (which has good points for cities)
        // and adjust them for new neighbors
        for (int k = 0; k < M; ++k) {
            int u = next_perm[k];
            int prev = next_perm[(k - 1 + M) % M];
            int next = next_perm[(k + 1) % M];
            int p_prev = next_sel[prev];
            int p_next = next_sel[next];
            
            int best_p = -1;
            double min_local = 1e18;
            int n_u = cities[u].n;
            int u_base = city_base_idx[u];
            int prev_idx_base = city_base_idx[prev] + p_prev;
            int next_idx_base = city_base_idx[next] + p_next;

            for (int p = 0; p < n_u; ++p) {
                // Cost from prev to u(p) + u(p) to next
                double c = cost_matrix[prev_idx_base * total_points + (u_base + p)] +
                           cost_matrix[(u_base + p) * total_points + next_idx_base];
                if (c < min_local) {
                    min_local = c;
                    best_p = p;
                }
            }
            next_sel[u] = best_p;
        }

        double next_cost = calculate_full_cost(next_perm, next_sel);
        double delta = next_cost - current_total_cost;
        
        if (delta < 0 || exp(-delta / temp) > ((double)rng() / mt19937::max())) {
            current_perm = next_perm;
            current_sel = next_sel;
            current_total_cost = next_cost;
            
            if (current_total_cost < best_cost) {
                // Polish with exact DP
                double polished_cost = optimize_points_exact(current_perm, current_sel);
                current_total_cost = polished_cost; // Update current as well
                
                if (polished_cost < best_cost) {
                    best_cost = polished_cost;
                    best_perm = current_perm;
                    best_sel = current_sel;
                }
            }
        }
        
        temp *= cooling_rate;
        if (temp < 1e-5) temp = 0.5; // restart
    }

    // Final Polish
    optimize_points_exact(best_perm, best_sel);

    for (int i = 0; i < M; ++i) {
        int u = best_perm[i];
        cout << "(" << cities[u].id << "," << best_sel[u] + 1 << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;

    return 0;
}