#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <chrono>

using namespace std;

// Problem constants
const int MAXN = 1005;

struct Clause {
    int lit1;
    int lit2;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> var_in_clauses; // Stores indices of clauses a variable appears in

// State
int assignment[MAXN]; // 0 or 1
int clause_sat_count[40005]; // How many literals satisfy clause i
int gain[MAXN]; // Improvement in satisfied clauses if variable i is flipped
int tabu[MAXN]; // Step number until which variable is tabu

// Global best
int best_assignment[MAXN];
int best_score = -1;

// Helper to check if a literal is true under current assignment
inline bool is_literal_true(int lit) {
    int var = abs(lit);
    int val = assignment[var];
    return (lit > 0) ? (val == 1) : (val == 0);
}

// Compute full score and gains from scratch
int compute_state() {
    int satisfied = 0;
    // Reset
    for (int i = 0; i < m; ++i) clause_sat_count[i] = 0;
    for (int i = 1; i <= n; ++i) gain[i] = 0;

    // Calc clause sat counts
    for (int i = 0; i < m; ++i) {
        bool t1 = is_literal_true(clauses[i].lit1);
        bool t2 = is_literal_true(clauses[i].lit2);
        if (t1) clause_sat_count[i]++;
        if (t2) clause_sat_count[i]++;
        if (clause_sat_count[i] > 0) satisfied++;
    }

    // Calc gains based on current baseline
    for (int i = 0; i < m; ++i) {
        int v1 = abs(clauses[i].lit1);
        int v2 = abs(clauses[i].lit2);
        int sat = clause_sat_count[i];
        bool sat_bool = (sat > 0);
        
        // Analyze v1 flip
        if (true) {
            int new_sat_v1 = 0;
            // if v1 flips
            // literal 1 flips if it uses v1
            bool l1_current = is_literal_true(clauses[i].lit1);
            bool l1_flipped = (abs(clauses[i].lit1) == v1) ? !l1_current : l1_current;
            if (l1_flipped) new_sat_v1++;
            
            bool l2_current = is_literal_true(clauses[i].lit2);
            bool l2_flipped = (abs(clauses[i].lit2) == v1) ? !l2_current : l2_current;
            if (l2_flipped) new_sat_v1++;
            
            int diff = (new_sat_v1 > 0) - sat_bool;
            gain[v1] += diff;
        }

        // Analyze v2 flip (if distinct)
        if (v1 != v2) {
            int new_sat_v2 = 0;
            // if v2 flips
            bool l1_current = is_literal_true(clauses[i].lit1);
            bool l1_flipped = (abs(clauses[i].lit1) == v2) ? !l1_current : l1_current;
            if (l1_flipped) new_sat_v2++;
            
            bool l2_current = is_literal_true(clauses[i].lit2);
            bool l2_flipped = (abs(clauses[i].lit2) == v2) ? !l2_current : l2_current;
            if (l2_flipped) new_sat_v2++;
            
            int diff = (new_sat_v2 > 0) - sat_bool;
            gain[v2] += diff;
        }
    }
    
    return satisfied;
}

// Flip variable v and update data structures
void flip(int v, int &current_total_sat) {
    assignment[v] = 1 - assignment[v];
    
    // Iterate over constraints involving v
    for (int c_idx : var_in_clauses[v]) {
        Clause &c = clauses[c_idx];
        int l1 = c.lit1;
        int l2 = c.lit2;
        int v1 = abs(l1);
        int v2 = abs(l2);
        
        int old_sat_count = clause_sat_count[c_idx];
        bool was_sat = (old_sat_count > 0);
        
        // Compute new sat count based on new assignment
        int new_sat_count = 0;
        bool l1_now = is_literal_true(l1);
        if (l1_now) new_sat_count++;
        bool l2_now = is_literal_true(l2);
        if (l2_now) new_sat_count++;
        
        clause_sat_count[c_idx] = new_sat_count;
        bool is_sat = (new_sat_count > 0);
        
        if (was_sat && !is_sat) current_total_sat--;
        else if (!was_sat && is_sat) current_total_sat++;
        
        // Reconstruct old truth values to remove OLD gain contributions
        // Since we only flipped v, we can deduce old truth.
        bool l1_was = (v1 == v) ? !l1_now : l1_now;
        bool l2_was = (v2 == v) ? !l2_now : l2_now;
        int s_old = (l1_was ? 1 : 0) + (l2_was ? 1 : 0);
        int s_new = new_sat_count;

        // Variables involved in this clause need their gains updated
        int distinct_vars[2];
        int d_count = 0;
        distinct_vars[d_count++] = v1;
        if (v2 != v1) distinct_vars[d_count++] = v2;
        
        for (int k = 0; k < d_count; ++k) {
            int u = distinct_vars[k];
            
            // Remove contribution from Old State
            // What was the change in sat if u was flipped in OLD state?
            bool l1_u_flip_old = (v1 == u) ? !l1_was : l1_was;
            bool l2_u_flip_old = (v2 == u) ? !l2_was : l2_was;
            int s_flip_old = (l1_u_flip_old ? 1 : 0) + (l2_u_flip_old ? 1 : 0);
            
            int diff_old = (s_flip_old > 0) - (s_old > 0);
            gain[u] -= diff_old;
            
            // Add contribution from New State
            // What is the change in sat if u is flipped in NEW state?
            bool l1_u_flip_new = (v1 == u) ? !l1_now : l1_now;
            bool l2_u_flip_new = (v2 == u) ? !l2_now : l2_now;
            int s_flip_new = (l1_u_flip_new ? 1 : 0) + (l2_u_flip_new ? 1 : 0);
            
            int diff_new = (s_flip_new > 0) - (s_new > 0);
            gain[u] += diff_new;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; 

    if (!(cin >> n >> m)) return 0;
    
    var_in_clauses.resize(n + 1);
    clauses.resize(m);
    
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].lit1 >> clauses[i].lit2;
        var_in_clauses[abs(clauses[i].lit1)].push_back(i);
        if (abs(clauses[i].lit2) != abs(clauses[i].lit1)) {
            var_in_clauses[abs(clauses[i].lit2)].push_back(i);
        }
    }

    if (m == 0) {
        for (int i=1; i<=n; i++) cout << 0 << (i==n?"":" ");
        cout << endl;
        return 0;
    }

    srand((unsigned)time(NULL));

    // Initial random assignment
    for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
    int current_sat = compute_state();
    
    best_score = current_sat;
    for (int i = 1; i <= n; ++i) best_assignment[i] = assignment[i];
    
    long long iter = 0;
    int tabu_tenure_base = 10;
    
    for(int i=0; i<=n; ++i) tabu[i] = 0;

    while (true) {
        if ((iter & 2047) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> duration = now - start_time;
            if (duration.count() > time_limit) break;
        }
        
        int best_non_tabu_var = -1;
        int best_non_tabu_gain = -1000000;
        int nt_count = 0;
        
        int best_tabu_var = -1;
        int best_tabu_gain = -1000000;
        int t_count = 0;
        
        for (int i = 1; i <= n; ++i) {
            int g = gain[i];
            bool is_tabu = (tabu[i] > iter);
            
            if (!is_tabu) {
                if (g > best_non_tabu_gain) {
                    best_non_tabu_gain = g;
                    best_non_tabu_var = i;
                    nt_count = 1;
                } else if (g == best_non_tabu_gain) {
                    nt_count++;
                    if (rand() % nt_count == 0) best_non_tabu_var = i;
                }
            } else {
                 if (g > best_tabu_gain) {
                    best_tabu_gain = g;
                    best_tabu_var = i;
                    t_count = 1;
                } else if (g == best_tabu_gain) {
                    t_count++;
                    if (rand() % t_count == 0) best_tabu_var = i;
                }
            }
        }
        
        int move_var = -1;
        bool aspiration = false;
        
        if (best_tabu_var != -1) {
            if (current_sat + best_tabu_gain > best_score) {
                move_var = best_tabu_var;
                aspiration = true;
            }
        }
        
        if (!aspiration) {
            if (best_non_tabu_var != -1) {
                move_var = best_non_tabu_var;
            } else {
                // Should effectively not happen with tabu tenure expiring
                move_var = (rand() % n) + 1;
            }
        }
        
        flip(move_var, current_sat);
        iter++;
        
        tabu[move_var] = iter + tabu_tenure_base + (rand() % 5);
        
        if (current_sat > best_score) {
            best_score = current_sat;
            for (int i = 1; i <= n; ++i) best_assignment[i] = assignment[i];
            if (best_score == m) break;
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}