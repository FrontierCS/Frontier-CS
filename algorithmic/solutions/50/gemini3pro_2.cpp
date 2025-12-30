#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Constants
const double TIME_LIMIT = 9.8; // Seconds

// Problem Data
int n, m;
vector<int> set_costs;
vector<vector<int>> set_to_elems;
vector<vector<int>> elem_to_sets;

// Solution Structure
struct Solution {
    vector<bool> selected;
    vector<int> coverage; // Number of selected sets covering each element
    long long total_cost;
    int selected_count;

    Solution() {
        selected.assign(m, false);
        coverage.assign(n, 0);
        total_cost = 0;
        selected_count = 0;
    }

    void add(int set_idx) {
        if (selected[set_idx]) return;
        selected[set_idx] = true;
        total_cost += set_costs[set_idx];
        selected_count++;
        for (int e : set_to_elems[set_idx]) {
            coverage[e]++;
        }
    }

    void remove(int set_idx) {
        if (!selected[set_idx]) return;
        selected[set_idx] = false;
        total_cost -= set_costs[set_idx];
        selected_count--;
        for (int e : set_to_elems[set_idx]) {
            coverage[e]--;
        }
    }

    bool is_redundant(int set_idx) const {
        for (int e : set_to_elems[set_idx]) {
            if (coverage[e] <= 1) return false;
        }
        return true;
    }
};

// Global Random Generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Timer
double get_time() {
    static auto start_time = chrono::steady_clock::now();
    return chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
}

// Remove redundant sets
void prune(Solution& sol) {
    vector<int> selected_indices;
    selected_indices.reserve(sol.selected_count);
    for (int i = 0; i < m; ++i) {
        if (sol.selected[i]) selected_indices.push_back(i);
    }
    
    // Try to remove most expensive redundant sets first
    sort(selected_indices.begin(), selected_indices.end(), [&](int a, int b) {
        return set_costs[a] > set_costs[b];
    });
    
    for (int s : selected_indices) {
        if (sol.is_redundant(s)) {
            sol.remove(s);
        }
    }
}

// Initial Solution Generation (Greedy with randomness)
void generate_initial_solution(Solution& sol) {
    sol = Solution();
    vector<int> uncovered;
    for (int i = 0; i < n; ++i) uncovered.push_back(i);

    while (!uncovered.empty()) {
        // Find an uncovered element to cover
        // Heuristic: Pick element with fewest available sets covering it
        int target_e = -1;
        int min_deg = m + 1;
        
        // Scan uncovered to find most constrained
        vector<int> current_uncovered;
        for (int i = 0; i < n; ++i) {
            if (sol.coverage[i] == 0) {
                int deg = elem_to_sets[i].size();
                if (deg < min_deg) {
                    min_deg = deg;
                    target_e = i;
                }
            }
        }
        
        if (target_e == -1) break; // All covered

        // Pick best set to cover target_e
        int best_set = -1;
        double best_score = 1e18;

        for (int s : elem_to_sets[target_e]) {
            if (sol.selected[s]) continue;
            
            int new_cover = 0;
            for (int e : set_to_elems[s]) {
                if (sol.coverage[e] == 0) new_cover++;
            }

            if (new_cover > 0) {
                // Cost per newly covered element
                double score = (double)set_costs[s] / new_cover;
                // Add noise for diversity
                score *= (1.0 + uniform_real_distribution<double>(0, 0.05)(rng));
                if (score < best_score) {
                    best_score = score;
                    best_set = s;
                }
            }
        }

        if (best_set != -1) {
            sol.add(best_set);
        } else {
            // This implies no valid cover exists, should not happen based on problem constraints
            break;
        }
    }
    prune(sol);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    if (!(cin >> n >> m)) return 0;

    set_costs.resize(m);
    long long sum_costs = 0;
    for (int i = 0; i < m; ++i) {
        cin >> set_costs[i];
        sum_costs += set_costs[i];
    }

    elem_to_sets.resize(n);
    set_to_elems.resize(m);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int s_id;
            cin >> s_id;
            --s_id; // Convert to 0-based index
            elem_to_sets[i].push_back(s_id);
            set_to_elems[s_id].push_back(i);
        }
    }

    // Initialize
    Solution best_sol;
    generate_initial_solution(best_sol);
    
    Solution current_sol = best_sol;

    // Simulated Annealing Parameters
    double avg_cost = (double)sum_costs / m;
    if (avg_cost < 1.0) avg_cost = 1.0;
    double temp_start = avg_cost * 2.0; 
    double temp = temp_start;

    // Timer Init
    get_time(); 

    int iter = 0;
    while (true) {
        iter++;
        // Check time every few iterations
        if ((iter & 63) == 0) {
            double t = get_time();
            if (t > TIME_LIMIT) break;
            
            // Temperature schedule: quadratic decay
            double progress = t / TIME_LIMIT;
            temp = temp_start * (1.0 - progress) * (1.0 - progress);
            if (temp < 0.1) temp = 0.1;
        }

        // Neighborhood Move: Destroy and Repair
        // 1. Remove a random set from current solution
        vector<int> selected_indices;
        for(int i=0; i<m; ++i) {
            if(current_sol.selected[i]) selected_indices.push_back(i);
        }
        
        if(selected_indices.empty()) break; 

        int rem_idx = uniform_int_distribution<int>(0, (int)selected_indices.size() - 1)(rng);
        int set_to_remove = selected_indices[rem_idx];

        Solution next_sol = current_sol;
        next_sol.remove(set_to_remove);

        // 2. Identify uncovered elements
        vector<int> uncovered;
        for(int i=0; i<n; ++i) {
            if(next_sol.coverage[i] == 0) uncovered.push_back(i);
        }

        // 3. Repair (Greedy fill)
        while(!uncovered.empty()) {
            // Pick a random uncovered element to drive the repair
            int u_idx = uniform_int_distribution<int>(0, (int)uncovered.size() - 1)(rng);
            int target = uncovered[u_idx];

            int best_s = -1;
            double best_score = 1e18;

            // Evaluate candidate sets covering 'target'
            for(int s : elem_to_sets[target]) {
                if(next_sol.selected[s]) continue;
                
                int gain = 0;
                for(int e : set_to_elems[s]) {
                    if(next_sol.coverage[e] == 0) gain++;
                }

                if(gain > 0) {
                    double sc = (double)set_costs[s] / gain;
                    // Add noise
                    sc *= (1.0 + uniform_real_distribution<double>(0, 0.05)(rng));
                    if(sc < best_score) {
                        best_score = sc;
                        best_s = s;
                    }
                }
            }

            if(best_s != -1) {
                next_sol.add(best_s);
                // Update uncovered list
                vector<int> remaining;
                remaining.reserve(uncovered.size());
                for(int u : uncovered) {
                    if(next_sol.coverage[u] == 0) remaining.push_back(u);
                }
                uncovered = remaining;
            } else {
                break; // Should not happen
            }
        }

        // 4. Prune redundant sets
        prune(next_sol);

        // 5. Acceptance Criteria (Metropolis)
        long long delta = next_sol.total_cost - current_sol.total_cost;
        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            if (uniform_real_distribution<double>(0.0, 1.0)(rng) < exp(-delta / temp)) {
                accept = true;
            }
        }

        if (accept) {
            current_sol = next_sol;
            if (current_sol.total_cost < best_sol.total_cost) {
                best_sol = current_sol;
            }
        }
    }

    // Output
    vector<int> ans;
    for(int i=0; i<m; ++i) {
        if(best_sol.selected[i]) ans.push_back(i + 1); // Output 1-based index
    }

    cout << ans.size() << endl;
    for(size_t i = 0; i < ans.size(); ++i) {
        cout << ans[i] << (i == ans.size() - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}