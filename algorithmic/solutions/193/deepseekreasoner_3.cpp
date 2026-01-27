#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Structure to represent a clause
struct Clause {
    int l1, l2; // Literals
    int v1, v2; // Variable indices (1-based)
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    vector<vector<int>> var_clauses(n + 1); // Adjacency list: var -> clause indices

    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l1 >> clauses[i].l2;
        clauses[i].v1 = abs(clauses[i].l1);
        clauses[i].v2 = abs(clauses[i].l2);
        var_clauses[clauses[i].v1].push_back(i);
        // Avoid adding the same clause index twice if the clause is like (x v x)
        if (clauses[i].v1 != clauses[i].v2) {
            var_clauses[clauses[i].v2].push_back(i);
        }
    }

    // Initialize random number generator
    srand(time(NULL));

    // Handle trivial case
    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << "0" << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    // State variables
    vector<int> assign(n + 1);
    vector<int> best_assign(n + 1); 
    // Initialize best_assign with 0s ensures valid output even if time limit is instant
    fill(best_assign.begin(), best_assign.end(), 0);
    
    int best_sat_count = -1;

    // Helper arrays for incremental updates
    vector<int> clause_sat_count(m);
    vector<int> gain(n + 1);

    double start_time = (double)clock() / CLOCKS_PER_SEC;
    double time_limit = 0.95; // Time limit slightly less than typical 1s to be safe

    // Lambda to compute gain impact of a specific clause
    auto compute_clause_impact = [&](int c_idx, int w, int current_cnt, bool w_curr_val) -> int {
        int v1 = clauses[c_idx].v1;
        int l1 = clauses[c_idx].l1;
        int v2 = clauses[c_idx].v2;
        int l2 = clauses[c_idx].l2;
        
        int delta = 0;
        // Check effect of first literal
        if (v1 == w) {
            bool val = (l1 > 0) ? w_curr_val : !w_curr_val;
            // If literal is currently true, flipping makes it false (delta -1)
            // If literal is currently false, flipping makes it true (delta +1)
            if (val) delta--; else delta++; 
        }
        // Check effect of second literal
        if (v2 == w) {
            bool val = (l2 > 0) ? w_curr_val : !w_curr_val;
            if (val) delta--; else delta++;
        }
        
        int future_cnt = current_cnt + delta;
        
        // Impact is change in satisfaction boolean
        // 1 if unsatisfied -> satisfied
        // -1 if satisfied -> unsatisfied
        // 0 otherwise (e.g., sat count 1->2 or 2->1)
        bool curr_sat = (current_cnt > 0);
        bool fut_sat = (future_cnt > 0);
        
        return (fut_sat ? 1 : 0) - (curr_sat ? 1 : 0);
    };

    // Main Local Search Loop (Hill Climbing with Random Restarts)
    while (true) {
        // Check time limit
        if (((double)clock() / CLOCKS_PER_SEC) - start_time > time_limit) break;

        // Random Restart
        for (int i = 1; i <= n; ++i) assign[i] = rand() % 2;

        // Initial Score Calculation
        int current_sat = 0;
        for (int i = 0; i < m; ++i) {
            bool s1 = (clauses[i].l1 > 0) ? assign[clauses[i].v1] : !assign[clauses[i].v1];
            bool s2 = (clauses[i].l2 > 0) ? assign[clauses[i].v2] : !assign[clauses[i].v2];
            int cnt = (s1 ? 1 : 0) + (s2 ? 1 : 0);
            clause_sat_count[i] = cnt;
            if (cnt > 0) current_sat++;
        }

        // Initial Gain Calculation
        fill(gain.begin(), gain.end(), 0);
        for (int i = 0; i < m; ++i) {
            int u = clauses[i].v1;
            int v = clauses[i].v2;
            
            int g_u = compute_clause_impact(i, u, clause_sat_count[i], assign[u]);
            gain[u] += g_u;
            
            if (u != v) {
                int g_v = compute_clause_impact(i, v, clause_sat_count[i], assign[v]);
                gain[v] += g_v;
            }
        }

        // Update Global Best
        if (current_sat > best_sat_count) {
            best_sat_count = current_sat;
            best_assign = assign;
            if (best_sat_count == m) break;
        }

        // Local Search Steps
        int max_flips = 50000; // Heuristic cap per restart
        for (int step = 0; step < max_flips; ++step) {
            // Find variable with best gain
            int best_v = -1;
            int best_g = -999999;
            int count_best = 0;

            // Linear scan is fast enough for N=1000
            for (int i = 1; i <= n; ++i) {
                if (gain[i] > best_g) {
                    best_g = gain[i];
                    best_v = i;
                    count_best = 1;
                } else if (gain[i] == best_g) {
                    count_best++;
                    // Reservoir sampling for tie-breaking
                    if (rand() % count_best == 0) best_v = i;
                }
            }

            // If no improvement possible, stop this restart (local optimum)
            if (best_g <= 0) break;

            // Perform Flip
            int flip_v = best_v;
            assign[flip_v] = !assign[flip_v];

            // Incremental Update
            for (int c_idx : var_clauses[flip_v]) {
                int old_sat = clause_sat_count[c_idx];
                
                // Calculate new sat count for this clause
                // Note: optimized re-eval is safer than delta logic for edge cases
                bool s1 = (clauses[c_idx].l1 > 0) ? assign[clauses[c_idx].v1] : !assign[clauses[c_idx].v1];
                bool s2 = (clauses[c_idx].l2 > 0) ? assign[clauses[c_idx].v2] : !assign[clauses[c_idx].v2];
                int new_sat = (s1 ? 1 : 0) + (s2 ? 1 : 0);

                if (new_sat == old_sat) continue;

                // Update global satisfaction count
                if (old_sat == 0 && new_sat > 0) current_sat++;
                else if (old_sat > 0 && new_sat == 0) current_sat--;

                // Update gains of involved variables
                int u = clauses[c_idx].v1;
                int v = clauses[c_idx].v2;

                // Previous values (before flip for u, v unchanged relative to before this clause update?)
                // Actually, assign[flip_v] is ALREADY flipped.
                // assign[other] is unchanged.
                // We need the "old" boolean values for the "old_sat" state context.
                // For flip_v, old value is !assign[flip_v]. For others, assign[v].
                
                bool u_val_old = (u == flip_v) ? !assign[u] : assign[u];
                bool v_val_old = (v == flip_v) ? !assign[v] : assign[v];

                // Remove old contribution
                gain[u] -= compute_clause_impact(c_idx, u, old_sat, u_val_old);
                if (u != v) gain[v] -= compute_clause_impact(c_idx, v, old_sat, v_val_old);

                // Add new contribution
                gain[u] += compute_clause_impact(c_idx, u, new_sat, assign[u]);
                if (u != v) gain[v] += compute_clause_impact(c_idx, v, new_sat, assign[v]);

                // Update clause count
                clause_sat_count[c_idx] = new_sat;
            }

            if (current_sat > best_sat_count) {
                best_sat_count = current_sat;
                best_assign = assign;
                if (best_sat_count == m) goto done;
            }
        }
    }

    done:;
    for (int i = 1; i <= n; ++i) {
        cout << best_assign[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}