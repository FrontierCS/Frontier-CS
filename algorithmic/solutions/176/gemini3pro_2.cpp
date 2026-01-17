#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <chrono>

using namespace std;

// Data structures to store clause information
struct Clause {
    int l[3];
};

// Occurrence structure to map variables to clauses
struct Occ {
    int clause_idx;
    int sign; // +1 if literal is x, -1 if literal is -x
};

// Global variables
int n, m;
vector<Clause> clauses;
vector<vector<Occ>> var_occ;
int current_assignment[1005];
int best_assignment[1005];
int clause_sat_count[10005]; // Number of satisfied literals in each clause
int current_sat;
int max_sat;

// Helper function to recalculate satisfaction counts from scratch
// Used after a random restart
void update_clause_counts() {
    current_sat = 0;
    for (int j = 0; j < m; ++j) {
        int sat_lits = 0;
        for (int k = 0; k < 3; ++k) {
            int lit = clauses[j].l[k];
            int var = abs(lit);
            int val = current_assignment[var];
            if (lit > 0 && val == 1) sat_lits++;
            if (lit < 0 && val == 0) sat_lits++;
        }
        clause_sat_count[j] = sat_lits;
        if (sat_lits > 0) current_sat++;
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Seed random number generator
    srand(time(NULL));

    if (!(cin >> n >> m)) return 0;

    // Resize vectors based on input size
    var_occ.resize(n + 1);
    clauses.resize(m);

    // Read clauses and build adjacency list
    for (int i = 0; i < m; ++i) {
        for (int k = 0; k < 3; ++k) {
            cin >> clauses[i].l[k];
            int var = abs(clauses[i].l[k]);
            int sign = (clauses[i].l[k] > 0) ? 1 : -1;
            var_occ[var].push_back({i, sign});
        }
    }

    // Initial random assignment
    for (int i = 1; i <= n; ++i) {
        current_assignment[i] = rand() % 2;
        best_assignment[i] = current_assignment[i];
    }

    update_clause_counts();
    max_sat = current_sat;

    // Timer setup for time-limited execution (assuming ~1s limit)
    auto start_time = chrono::steady_clock::now();
    double time_limit = 0.90; // Stop slightly before 1 second

    // Vector to store variable indices for random traversal
    vector<int> p(n);
    for(int i=0; i<n; ++i) p[i] = i+1;

    // Main optimization loop (Hill Climbing with Random Restarts)
    while (true) {
        // Check time limit
        auto now = chrono::steady_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > time_limit) break;

        bool local_improvement = false;
        
        // Shuffle variable order to prevent bias and cycling
        for (int i = n - 1; i > 0; i--) {
            int j = rand() % (i + 1);
            swap(p[i], p[j]);
        }

        // Try to flip each variable to improve score
        for (int i : p) {
            int gain = 0;
            
            // Calculate potential gain efficiently without full re-evaluation
            for (const auto& occ : var_occ[i]) {
                int c_idx = occ.clause_idx;
                int sign = occ.sign; 
                
                // Determine if the literal involving x_i is currently True or False
                int val_sign = (current_assignment[i] == 1) ? 1 : -1;
                bool is_lit_true = (sign == val_sign);
                
                if (is_lit_true) {
                    // Literal is currently TRUE, flip makes it FALSE. 
                    // If it was the only true literal in the clause, clause becomes unsatisfied.
                    if (clause_sat_count[c_idx] == 1) gain--;
                } else {
                    // Literal is currently FALSE, flip makes it TRUE.
                    // If clause was unsatisfied (0 true literals), it becomes satisfied.
                    if (clause_sat_count[c_idx] == 0) gain++;
                }
            }

            // If flipping improves the solution (Greedy Step)
            if (gain > 0) {
                // Perform flip
                current_assignment[i] = 1 - current_assignment[i];
                current_sat += gain;
                
                // Update clause satisfied literal counts
                for (const auto& occ : var_occ[i]) {
                    int c_idx = occ.clause_idx;
                    int sign = occ.sign;
                    int val_sign = (current_assignment[i] == 1) ? 1 : -1;
                    
                    if (sign == val_sign) {
                        // Literal became true
                        clause_sat_count[c_idx]++;
                    } else {
                        // Literal became false
                        clause_sat_count[c_idx]--;
                    }
                }
                
                local_improvement = true;
            }
        }

        // Update best found solution
        if (current_sat > max_sat) {
            max_sat = current_sat;
            for (int i = 1; i <= n; ++i) best_assignment[i] = current_assignment[i];
            if (max_sat == m) break; // Optimal solution found
        }

        // If local optimum reached (no single flip improves score), perform random restart
        if (!local_improvement) {
            for (int i = 1; i <= n; ++i) {
                current_assignment[i] = rand() % 2;
            }
            update_clause_counts();
        }
    }

    // Output the best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}