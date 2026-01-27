#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Clause structure: l1, l2 are literal encodings, u1, u2 are variable indices
struct Clause {
    int l1, l2;
    int u1, u2;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> var_clauses;
vector<int> assignment;
vector<int> best_assignment;
int current_sat = 0;
int max_sat = -1;
vector<int> sat_count;
vector<int> gain;
vector<int> tabu;

// Helper: check if literal is true
// type 0: positive variable (x), type 1: negative variable (-x)
// var_val: current value of variable (0 or 1)
inline int is_true(int var_val, int type) {
    return var_val != type;
}

// Compute satisfied literal count for a clause
inline int get_clause_sat(int c_idx) {
    int v1 = clauses[c_idx].u1;
    int t1 = clauses[c_idx].l1 & 1;
    
    int v2 = clauses[c_idx].u2;
    int t2 = clauses[c_idx].l2 & 1;
    
    return is_true(assignment[v1], t1) + is_true(assignment[v2], t2);
}

// Calculate the gain (delta score) if variable 'u' is flipped
// s: current number of satisfied literals in the clause
// u_curr_val: current assignment of u
inline int calc_contrib(int c_idx, int u, int s, int u_curr_val) {
    int v1 = clauses[c_idx].u1;
    int t1 = clauses[c_idx].l1 & 1;
    int val1 = is_true(assignment[v1], t1);
    
    int v2 = clauses[c_idx].u2;
    int t2 = clauses[c_idx].l2 & 1;
    int val2 = is_true(assignment[v2], t2);
    
    // Determine new values if u is flipped
    // If v1 == u, its literal value flips
    int val1_new = (v1 == u) ? 1 - val1 : val1;
    int val2_new = (v2 == u) ? 1 - val2 : val2;
    
    int s_new = val1_new + val2_new;
    
    // Gain is 1 if clause becomes satisfied (0->1,2), -1 if becomes unsatisfied (1,2->0), 0 otherwise
    int is_sat_curr = (s > 0);
    int is_sat_new = (s_new > 0);
    
    return is_sat_new - is_sat_curr;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    var_clauses.resize(n);
    for(int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        // Map 1-based literals to 0-based variables and types
        int type1 = (u > 0) ? 0 : 1;
        int var1 = abs(u) - 1;
        int type2 = (v > 0) ? 0 : 1;
        int var2 = abs(v) - 1;
        
        // Encode literal: (var << 1) | type
        clauses[i] = { (var1 << 1) | type1, (var2 << 1) | type2, var1, var2 };
        
        var_clauses[var1].push_back(i);
        if (var2 != var1) var_clauses[var2].push_back(i);
    }

    assignment.resize(n);
    sat_count.resize(m);
    gain.resize(n);
    best_assignment.resize(n); 
    tabu.resize(n, 0);

    // Random number generator
    mt19937 rng(1337);

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 0.95; // Stop before 1s

    // Main Loop: Restarts
    while (true) {
        // Time Check
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration<double>(now - start_time).count() > time_limit) break;

        // Initialize random assignment
        for(int i = 0; i < n; ++i) assignment[i] = rng() % 2;

        // Calculate initial scores
        current_sat = 0;
        fill(sat_count.begin(), sat_count.end(), 0);
        for(int i = 0; i < m; ++i) {
            sat_count[i] = get_clause_sat(i);
            if (sat_count[i] > 0) current_sat++;
        }

        if (current_sat > max_sat) {
            max_sat = current_sat;
            best_assignment = assignment;
        }

        // Calculate initial gains
        fill(gain.begin(), gain.end(), 0);
        for(int u = 0; u < n; ++u) {
            for(int c_idx : var_clauses[u]) {
                gain[u] += calc_contrib(c_idx, u, sat_count[c_idx], assignment[u]);
            }
        }

        // Tabu Search / Local Search
        fill(tabu.begin(), tabu.end(), 0);
        int iter = 0;
        int no_impr = 0;

        while (true) {
            iter++;
            // Check time periodically
            if ((iter & 1023) == 0) {
                 auto curr = chrono::high_resolution_clock::now();
                 if (chrono::duration<double>(curr - start_time).count() > time_limit) break;
            }
            if (no_impr > 2000) break; // Restart if stuck

            // Find best variable to flip
            int best_v = -1;
            int best_val = -1e9;
            vector<int> ties;

            for(int i = 0; i < n; ++i) {
                bool is_tabu = (tabu[i] > iter);
                // Aspiration criterion: allow tabu move if it improves global best
                if (is_tabu && (current_sat + gain[i] > max_sat)) {
                    is_tabu = false;
                }

                if (!is_tabu) {
                    if (gain[i] > best_val) {
                        best_val = gain[i];
                        best_v = i;
                        ties.clear();
                        ties.push_back(i);
                    } else if (gain[i] == best_val) {
                        ties.push_back(i);
                    }
                }
            }

            // Handle case where no move is available (all tabu) or generic ties
            if (best_v == -1) {
                // Pick random to break deadlock
                best_v = rng() % n;
            } else if (!ties.empty()) {
                best_v = ties[rng() % ties.size()];
            }

            int v = best_v;
            
            // Incremental Update Calculation
            
            // 1. Subtract contributions of affected clauses from neighbors (based on OLD state)
            for(int c_idx : var_clauses[v]) {
                int u1 = clauses[c_idx].u1;
                int u2 = clauses[c_idx].u2;
                
                gain[u1] -= calc_contrib(c_idx, u1, sat_count[c_idx], assignment[u1]);
                if (u2 != u1) {
                    gain[u2] -= calc_contrib(c_idx, u2, sat_count[c_idx], assignment[u2]);
                }
            }

            // 2. Perform flip
            assignment[v] = 1 - assignment[v];

            // 3. Update sat counts and current score
            for(int c_idx : var_clauses[v]) {
                int old_s = sat_count[c_idx];
                sat_count[c_idx] = get_clause_sat(c_idx); // uses new assignment
                int new_s = sat_count[c_idx];
                
                if (old_s == 0 && new_s > 0) current_sat++;
                if (old_s > 0 && new_s == 0) current_sat--;
            }

            // 4. Add contributions of affected clauses to neighbors (based on NEW state)
            for(int c_idx : var_clauses[v]) {
                int u1 = clauses[c_idx].u1;
                int u2 = clauses[c_idx].u2;
                
                gain[u1] += calc_contrib(c_idx, u1, sat_count[c_idx], assignment[u1]);
                if (u2 != u1) {
                    gain[u2] += calc_contrib(c_idx, u2, sat_count[c_idx], assignment[u2]);
                }
            }

            // Check global best
            if (current_sat > max_sat) {
                max_sat = current_sat;
                best_assignment = assignment;
                no_impr = 0;
            } else {
                no_impr++;
            }

            // Update tabu tenure
            tabu[v] = iter + 5 + rng() % 10;
        }
    }

    // Output result
    for(int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}