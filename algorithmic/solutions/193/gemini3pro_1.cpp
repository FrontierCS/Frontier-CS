#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

using namespace std;

// Structure to represent a clause
struct Clause {
    int l1, l2;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> var_to_clauses; // Stores indices of clauses where each variable appears

// Current state
vector<int> current_assignment; // 1-based index for variables
vector<int> current_clause_sat; // Number of satisfied literals in each clause
int current_sat_count = 0;      // Total number of satisfied clauses

// Best solution found so far
vector<int> best_assignment;
int max_satisfied = -1;

// Helper to determine if a literal is true under the given assignment
inline int is_true(int literal, const vector<int>& assign) {
    int var = abs(literal);
    int val = assign[var];
    // if literal > 0 (e.g. 5), true if val is 1
    // if literal < 0 (e.g. -5), true if val is 0
    return (literal > 0) ? val : (1 - val);
}

// Compute the full state (clause satisfaction counts) from scratch
void compute_full_state() {
    current_sat_count = 0;
    for (int i = 0; i < m; ++i) {
        int sat = is_true(clauses[i].l1, current_assignment) + is_true(clauses[i].l2, current_assignment);
        current_clause_sat[i] = sat;
        if (sat > 0) current_sat_count++;
    }
}

// Calculate the net gain in satisfied clauses if variable `var` is flipped
inline int get_gain(int var) {
    int gain = 0;
    int old_val = current_assignment[var];
    int new_val = 1 - old_val;

    for (int c_idx : var_to_clauses[var]) {
        int s = current_clause_sat[c_idx];
        int l1 = clauses[c_idx].l1;
        int l2 = clauses[c_idx].l2;
        
        int contrib_old = 0;
        int contrib_new = 0;

        // Calculate contribution of this variable to the clause's satisfaction
        if (abs(l1) == var) {
            contrib_old += (l1 > 0 ? old_val : 1 - old_val);
            contrib_new += (l1 > 0 ? new_val : 1 - new_val);
        }
        if (abs(l2) == var) {
            contrib_old += (l2 > 0 ? old_val : 1 - old_val);
            contrib_new += (l2 > 0 ? new_val : 1 - new_val);
        }

        int new_s = s - contrib_old + contrib_new;
        
        // Clause status change:
        // Satisfied (s > 0) -> Unsatisfied (new_s == 0): gain decreases
        // Unsatisfied (s == 0) -> Satisfied (new_s > 0): gain increases
        if (s == 0 && new_s > 0) gain++;
        else if (s > 0 && new_s == 0) gain--;
    }
    return gain;
}

// Flip the variable `var` and update the state
inline void flip(int var) {
    int old_val = current_assignment[var];
    int new_val = 1 - old_val;
    current_assignment[var] = new_val;

    for (int c_idx : var_to_clauses[var]) {
        int s = current_clause_sat[c_idx];
        int l1 = clauses[c_idx].l1;
        int l2 = clauses[c_idx].l2;
        
        int contrib_old = 0;
        int contrib_new = 0;

        if (abs(l1) == var) {
            contrib_old += (l1 > 0 ? old_val : 1 - old_val);
            contrib_new += (l1 > 0 ? new_val : 1 - new_val);
        }
        if (abs(l2) == var) {
            contrib_old += (l2 > 0 ? old_val : 1 - old_val);
            contrib_new += (l2 > 0 ? new_val : 1 - new_val);
        }

        int new_s = s - contrib_old + contrib_new;
        
        if (s == 0 && new_s > 0) current_sat_count++;
        else if (s > 0 && new_s == 0) current_sat_count--;
        
        current_clause_sat[c_idx] = new_s;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    var_to_clauses.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l1 >> clauses[i].l2;
        var_to_clauses[abs(clauses[i].l1)].push_back(i);
        // Add to the second variable's list only if it's different from the first
        if (abs(clauses[i].l2) != abs(clauses[i].l1)) {
            var_to_clauses[abs(clauses[i].l2)].push_back(i);
        }
    }

    // Handle edge case where there are no clauses
    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << 0 << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    current_assignment.resize(n + 1);
    current_clause_sat.resize(m);
    best_assignment.resize(n + 1);

    // Initialize RNG
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Initial random assignment
    for (int i = 1; i <= n; ++i) current_assignment[i] = rng() % 2;
    compute_full_state();
    
    best_assignment = current_assignment;
    max_satisfied = current_sat_count;

    auto start_time = chrono::steady_clock::now();
    
    // Variables list to shuffle for random order traversal
    vector<int> vars(n);
    iota(vars.begin(), vars.end(), 1);

    // Main optimization loop (Iterated Local Search)
    while (true) {
        // Time check (using 0.95 seconds as a safe threshold for a typical 1s limit)
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration<double>(curr_time - start_time).count() > 0.95) break;

        // Hill Climbing Phase: Greedily flip variables that improve the score
        bool local_improvement = true;
        while (local_improvement) {
            local_improvement = false;
            shuffle(vars.begin(), vars.end(), rng); // Random order to avoid bias
            
            for (int v : vars) {
                if (get_gain(v) > 0) {
                    flip(v);
                    local_improvement = true;
                    // Check global best immediately
                    if (current_sat_count > max_satisfied) {
                        max_satisfied = current_sat_count;
                        best_assignment = current_assignment;
                    }
                }
            }
        }

        if (max_satisfied == m) break; // Optimal solution found

        // Perturbation / Restart Phase to escape local optima
        // 10% chance to do a full random restart, 90% chance to perturb current solution
        if (rng() % 100 < 10) {
            // Full Restart
            for (int i = 1; i <= n; ++i) current_assignment[i] = rng() % 2;
            compute_full_state();
        } else {
            // Perturb: Flip a small number of random variables (e.g., 1-5% of n)
            int k = 1 + rng() % (max(1, n / 20)); 
            for (int i = 0; i < k; ++i) {
                int v = 1 + rng() % n;
                flip(v); // Force flip even if it decreases score
            }
            // Next loop iteration will hill-climb from this new state
        }
    }

    // Output the best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}