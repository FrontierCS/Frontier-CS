#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Structure to store clause information
struct Clause {
    int lits[3];
    bool sat;
    int unassigned_count;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> pos_occ; // Clauses containing variable i as positive literal
vector<vector<int>> neg_occ; // Clauses containing variable i as negative literal
vector<int> assignment;      // Current assignment: 0 or 1
vector<int> sat_count_per_clause; // Number of true literals in each clause
vector<int> affected;        // List of clauses affected by current variable flip
vector<int> visited_stamp;   // For efficient deduplication of affected clauses
int current_stamp = 0;

// Returns the weight contribution for a clause with k unassigned literals.
// Based on 2^(3-k) scaling: k=3 -> 1, k=2 -> 2, k=1 -> 4.
// This corresponds to the probability of the clause remaining unsatisfied.
int get_weight(int k) {
    if (k == 1) return 4;
    if (k == 2) return 2;
    if (k == 3) return 1;
    return 0;
}

int main() {
    // optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    pos_occ.resize(n + 1);
    neg_occ.resize(n + 1);
    assignment.assign(n + 1, -1);
    visited_stamp.assign(m, 0);

    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].lits[0] >> clauses[i].lits[1] >> clauses[i].lits[2];
        clauses[i].sat = false;
        clauses[i].unassigned_count = 3; 
        
        for (int j = 0; j < 3; ++j) {
            int lit = clauses[i].lits[j];
            if (lit > 0) pos_occ[lit].push_back(i);
            else neg_occ[-lit].push_back(i);
        }
    }

    // Phase 1: Deterministic Method of Conditional Expectations
    // This provides a good initial assignment satisfying at least 7/8 of clauses (for 3-SAT)
    for (int i = 1; i <= n; ++i) {
        long long weight_true = 0;
        long long weight_false = 0;

        // Calculate 'cost' (expected unsatisfied clauses) if x_i = TRUE
        // Satisfies clauses in pos_occ (cost drops to 0)
        // Shrinks clauses in neg_occ (cost increases)
        // We compare the reduction in potential energy.
        // Actually, we choose the value that maximizes the weight of clauses satisfied minus weight increase of shrunk clauses.
        // Simplified: maximize sum of weights of potentially satisfied clauses vs potentially shrunk clauses.
        
        for (int c_idx : pos_occ[i]) {
            if (!clauses[c_idx].sat) {
                weight_true += get_weight(clauses[c_idx].unassigned_count);
            }
        }
        for (int c_idx : neg_occ[i]) {
            if (!clauses[c_idx].sat) {
                weight_false += get_weight(clauses[c_idx].unassigned_count);
            }
        }

        bool val = (weight_true >= weight_false);
        assignment[i] = val ? 1 : 0;

        // Update clause states based on choice
        if (val) { // Chosen TRUE
            for (int c_idx : pos_occ[i]) clauses[c_idx].sat = true;
            for (int c_idx : neg_occ[i]) {
                if (!clauses[c_idx].sat) clauses[c_idx].unassigned_count--;
            }
        } else { // Chosen FALSE
            for (int c_idx : neg_occ[i]) clauses[c_idx].sat = true;
            for (int c_idx : pos_occ[i]) {
                if (!clauses[c_idx].sat) clauses[c_idx].unassigned_count--;
            }
        }
    }

    // Phase 2: Local Search (Hill Climbing) to improve the solution
    // Compute initial satisfaction counts
    sat_count_per_clause.assign(m, 0);
    for(int i=0; i<m; ++i) {
        int s = 0;
        for(int j=0; j<3; ++j) {
            int lit = clauses[i].lits[j];
            int var = abs(lit);
            int val = assignment[var];
            if ((lit > 0 && val == 1) || (lit < 0 && val == 0)) s++;
        }
        sat_count_per_clause[i] = s;
    }

    // Iteratively flip variables if it strictly improves the number of satisfied clauses
    for (int iter = 0; iter < 100; ++iter) {
        bool improved = false;
        for (int i = 1; i <= n; ++i) {
            current_stamp++;
            affected.clear();
            
            // Identify unique clauses affected by variable i
            for (int c_idx : pos_occ[i]) {
                if (visited_stamp[c_idx] != current_stamp) {
                    visited_stamp[c_idx] = current_stamp;
                    affected.push_back(c_idx);
                }
            }
            for (int c_idx : neg_occ[i]) {
                if (visited_stamp[c_idx] != current_stamp) {
                    visited_stamp[c_idx] = current_stamp;
                    affected.push_back(c_idx);
                }
            }

            int gain = 0;
            int current_val = assignment[i];
            int next_val = 1 - current_val;
            
            // Calculate net gain of flipping x_i
            for (int c_idx : affected) {
                bool was_sat = (sat_count_per_clause[c_idx] > 0);
                int delta = 0;
                // Calculate change in satisfied literals for this clause
                for(int j=0; j<3; ++j) {
                    int lit = clauses[c_idx].lits[j];
                    if (abs(lit) == i) {
                        // If literal is currently true, it will become false -> delta -1
                        // If literal is currently false, it will become true -> delta +1
                        bool lit_is_true = (lit > 0 && current_val == 1) || (lit < 0 && current_val == 0);
                        if (lit_is_true) delta--;
                        else delta++;
                    }
                }
                bool will_sat = (sat_count_per_clause[c_idx] + delta > 0);
                if (will_sat && !was_sat) gain++;
                if (!will_sat && was_sat) gain--;
            }

            // If flipping improves the score, do it
            if (gain > 0) {
                assignment[i] = next_val;
                improved = true;
                // Update sat counts
                for (int c_idx : affected) {
                    int delta = 0;
                    for(int j=0; j<3; ++j) {
                        int lit = clauses[c_idx].lits[j];
                        if (abs(lit) == i) {
                            bool lit_now_true = (lit > 0 && next_val == 1) || (lit < 0 && next_val == 0);
                            if (lit_now_true) delta++; 
                            else delta--;
                        }
                    }
                    sat_count_per_clause[c_idx] += delta;
                }
            }
        }
        if (!improved) break;
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}