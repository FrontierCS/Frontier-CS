#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// Constants
const int MAXN = 405;
const int MAXM = 4005;
const double TIME_LIMIT = 9.8; // seconds

// Inputs
int n, m;
long long set_costs[MAXM];
bitset<MAXN> set_covers[MAXM];

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Structure to represent a solution state
struct State {
    vector<int> selected_sets;
    vector<int> coverage_count; // coverage_count[i] stores how many selected sets cover element i
    long long total_cost;
    
    State() {
        coverage_count.assign(n + 1, 0);
        total_cost = 0;
    }
    
    // Add a set to the solution
    void add(int set_id) {
        selected_sets.push_back(set_id);
        total_cost += set_costs[set_id];
        // Only iterate up to n, but bits are 1-based usually
        // Bitset indices 1..n
        for (int i = 1; i <= n; ++i) {
            if (set_covers[set_id][i]) {
                coverage_count[i]++;
            }
        }
    }
    
    // Remove a set from the solution at a specific index in selected_sets
    void remove_at(int idx) {
        int set_id = selected_sets[idx];
        // Swap with back for O(1) removal
        selected_sets[idx] = selected_sets.back();
        selected_sets.pop_back();
        
        total_cost -= set_costs[set_id];
        for (int i = 1; i <= n; ++i) {
            if (set_covers[set_id][i]) {
                coverage_count[i]--;
            }
        }
    }

    // Check if a specific set in solution is redundant
    bool is_redundant(int set_id) const {
        for (int i = 1; i <= n; ++i) {
            if (set_covers[set_id][i]) {
                if (coverage_count[i] <= 1) return false;
            }
        }
        return true;
    }

    // Prune redundant sets. 
    // Heuristic: Try to remove most expensive sets first.
    void prune() {
        if (selected_sets.empty()) return;
        
        // Sort selected sets by cost descending to try removing expensive ones first
        sort(selected_sets.begin(), selected_sets.end(), [](int a, int b) {
            return set_costs[a] > set_costs[b];
        });
        
        for (int i = 0; i < (int)selected_sets.size(); ) {
            int set_id = selected_sets[i];
            if (is_redundant(set_id)) {
                remove_at(i);
                // After removal, element at i is replaced by back, so check i again.
            } else {
                i++;
            }
        }
    }

    // Returns a bitset of uncovered elements
    bitset<MAXN> get_uncovered_mask() const {
        bitset<MAXN> unc;
        for(int i=1; i<=n; ++i) {
            if(coverage_count[i] == 0) unc.set(i);
        }
        return unc;
    }
};

// Global best tracker
long long best_cost = -1;
vector<int> best_solution;

void update_best(const State& s) {
    if (best_cost == -1 || s.total_cost < best_cost) {
        best_cost = s.total_cost;
        best_solution = s.selected_sets;
    }
}

// Fills the holes (uncovered elements) in state s using a randomized greedy heuristic
void fill_holes(State& s) {
    bitset<MAXN> uncovered = s.get_uncovered_mask();
    vector<bool> is_selected(m + 1, false);
    for(int id : s.selected_sets) is_selected[id] = true;

    while (uncovered.any()) {
        struct Cand {
            int id;
            double score; // elements covered per unit cost
        };
        vector<Cand> cands;
        cands.reserve(m);
        
        // Find candidates that cover at least one uncovered element
        // Iterate all unselected sets
        for (int j = 1; j <= m; ++j) {
            if (is_selected[j]) continue;
            
            // Check intersection with uncovered
            int count = (set_covers[j] & uncovered).count();
            if (count == 0) continue;
            
            // Heuristic score: higher is better
            // Adding a small epsilon to cost to avoid division by zero (though costs usually > 0)
            double score = (double)count / (double)(set_costs[j] + 1e-9);
            cands.push_back({j, score});
        }
        
        if (cands.empty()) break; // Should not happen if a valid cover exists
        
        // Select from top candidates randomly to introduce diversity
        int limit = min((int)cands.size(), 4); 
        // Partial sort to get top 'limit' candidates
        partial_sort(cands.begin(), cands.begin() + limit, cands.end(), [](const Cand& a, const Cand& b){
            return a.score > b.score;
        });
        
        int pick_idx = uniform_int_distribution<int>(0, limit - 1)(rng);
        int picked_id = cands[pick_idx].id;
        
        s.add(picked_id);
        is_selected[picked_id] = true;
        
        // Update uncovered mask
        uncovered &= ~set_covers[picked_id];
    }
}

// Generate an initial valid solution
State generate_random_greedy() {
    State s;
    fill_holes(s);
    s.prune();
    return s;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();

    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= m; ++i) {
        cin >> set_costs[i];
    }

    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int set_id;
            cin >> set_id;
            set_covers[set_id].set(i);
        }
    }

    // Initial Solution
    State current_state = generate_random_greedy();
    update_best(current_state);
    
    // Simulated Annealing Parameters
    double temp = max(1.0, (double)current_state.total_cost * 0.05);
    double cooling_rate = 0.9995; 

    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 127) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > TIME_LIMIT) break;
        }

        // Create neighbor: Perturb current state
        State neighbor = current_state;
        
        // Strategy: Remove k random sets, then fill holes
        int k = 1;
        // Occasionally remove more
        if (neighbor.selected_sets.size() > 5 && uniform_int_distribution<int>(0, 20)(rng) == 0) {
            k = 2 + uniform_int_distribution<int>(0, 3)(rng);
        }
        
        for (int i = 0; i < k && !neighbor.selected_sets.empty(); ++i) {
            int idx = uniform_int_distribution<int>(0, neighbor.selected_sets.size() - 1)(rng);
            neighbor.remove_at(idx);
        }
        
        fill_holes(neighbor);
        neighbor.prune();
        
        update_best(neighbor);

        // Metropolis Acceptance
        long long diff = neighbor.total_cost - current_state.total_cost;
        if (diff <= 0) {
            current_state = neighbor;
        } else {
            double prob = exp(-diff / temp);
            if (uniform_real_distribution<double>(0.0, 1.0)(rng) < prob) {
                current_state = neighbor;
            }
        }
        
        temp *= cooling_rate;
        // Reheat if stuck
        if (temp < 1e-3) temp = max(1.0, (double)best_cost * 0.02);
    }
    
    cout << best_solution.size() << "\n";
    for (int i = 0; i < (int)best_solution.size(); ++i) {
        cout << best_solution[i] << (i == (int)best_solution.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}