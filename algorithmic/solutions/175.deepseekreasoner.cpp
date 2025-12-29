#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    scanf("%d %d", &n, &m);
    if (m == 0) {
        for (int i = 0; i < n; ++i) printf("0 ");
        printf("\n");
        return 0;
    }
    
    vector<array<int,3>> vars(m);
    vector<array<bool,3>> signs(m);
    vector<vector<int>> pos_adj(n+1), neg_adj(n+1);
    
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        scanf("%d %d %d", &a, &b, &c);
        array<int,3> lits = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int var = abs(lit);
            bool sign = (lit > 0);
            vars[i][j] = var;
            signs[i][j] = sign;
            if (sign) {
                pos_adj[var].push_back(i);
            } else {
                neg_adj[var].push_back(i);
            }
        }
    }
    
    // Initial greedy assignment
    vector<int> val(n+1);
    for (int v = 1; v <= n; ++v) {
        int cnt_pos = pos_adj[v].size();
        int cnt_neg = neg_adj[v].size();
        val[v] = (cnt_pos >= cnt_neg) ? 1 : 0;
    }
    
    // Compute true_count and initialize unsat list
    vector<int> true_count(m, 0);
    vector<int> unsat_list;
    vector<int> pos_in_unsat(m, -1);
    
    for (int i = 0; i < m; ++i) {
        int cnt = 0;
        for (int j = 0; j < 3; ++j) {
            int v = vars[i][j];
            bool sign = signs[i][j];
            if ((sign && val[v]==1) || (!sign && val[v]==0)) cnt++;
        }
        true_count[i] = cnt;
        if (cnt == 0) {
            pos_in_unsat[i] = unsat_list.size();
            unsat_list.push_back(i);
        }
    }
    
    // Keep track of best assignment found
    int best_unsat = unsat_list.size();
    vector<int> best_val = val;
    
    // Random generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> rand_real(0.0, 1.0);
    uniform_int_distribution<int> rand_three(0, 2);
    
    const int MAX_ITER = 10000;
    const double NOISE = 0.3;
    
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        if (unsat_list.empty()) break;
        
        // pick random unsatisfied clause
        uniform_int_distribution<int> rand_unsat(0, unsat_list.size()-1);
        int c = unsat_list[rand_unsat(rng)];
        
        int flip_var;
        if (rand_real(rng) < NOISE) {
            int idx = rand_three(rng);
            flip_var = vars[c][idx];
        } else {
            int best_gain = -1e9;
            vector<int> best_vars;
            for (int idx = 0; idx < 3; ++idx) {
                int v = vars[c][idx];
                int gain = 0;
                int cur_val = val[v];
                int new_val = 1 - cur_val;
                // positive occurrences
                for (int clause_idx : pos_adj[v]) {
                    int old_true = true_count[clause_idx];
                    int delta = new_val - cur_val;
                    int new_true = old_true + delta;
                    bool old_sat = (old_true >= 1);
                    bool new_sat = (new_true >= 1);
                    if (new_sat && !old_sat) gain++;
                    else if (!new_sat && old_sat) gain--;
                }
                // negative occurrences
                for (int clause_idx : neg_adj[v]) {
                    int old_true = true_count[clause_idx];
                    int delta = cur_val - new_val;
                    int new_true = old_true + delta;
                    bool old_sat = (old_true >= 1);
                    bool new_sat = (new_true >= 1);
                    if (new_sat && !old_sat) gain++;
                    else if (!new_sat && old_sat) gain--;
                }
                if (gain > best_gain) {
                    best_gain = gain;
                    best_vars.clear();
                    best_vars.push_back(v);
                } else if (gain == best_gain) {
                    best_vars.push_back(v);
                }
            }
            // pick random among best
            uniform_int_distribution<int> rand_best(0, best_vars.size()-1);
            flip_var = best_vars[rand_best(rng)];
        }
        
        // Flip variable flip_var
        int old_val = val[flip_var];
        int new_val = 1 - old_val;
        
        // Update clauses where flip_var appears positively
        for (int clause_idx : pos_adj[flip_var]) {
            int old_true = true_count[clause_idx];
            int delta = new_val - old_val;
            int new_true = old_true + delta;
            true_count[clause_idx] = new_true;
            
            if (old_true == 0 && new_true > 0) {
                // clause became satisfied
                int p = pos_in_unsat[clause_idx];
                if (p != -1) {
                    // remove from unsat_list
                    int last = unsat_list.back();
                    unsat_list[p] = last;
                    pos_in_unsat[last] = p;
                    unsat_list.pop_back();
                    pos_in_unsat[clause_idx] = -1;
                }
            } else if (old_true > 0 && new_true == 0) {
                // clause became unsatisfied
                if (pos_in_unsat[clause_idx] == -1) {
                    pos_in_unsat[clause_idx] = unsat_list.size();
                    unsat_list.push_back(clause_idx);
                }
            }
        }
        
        // Update clauses where flip_var appears negatively
        for (int clause_idx : neg_adj[flip_var]) {
            int old_true = true_count[clause_idx];
            int delta = old_val - new_val;
            int new_true = old_true + delta;
            true_count[clause_idx] = new_true;
            
            if (old_true == 0 && new_true > 0) {
                // clause became satisfied
                int p = pos_in_unsat[clause_idx];
                if (p != -1) {
                    int last = unsat_list.back();
                    unsat_list[p] = last;
                    pos_in_unsat[last] = p;
                    unsat_list.pop_back();
                    pos_in_unsat[clause_idx] = -1;
                }
            } else if (old_true > 0 && new_true == 0) {
                // clause became unsatisfied
                if (pos_in_unsat[clause_idx] == -1) {
                    pos_in_unsat[clause_idx] = unsat_list.size();
                    unsat_list.push_back(clause_idx);
                }
            }
        }
        
        val[flip_var] = new_val;
        
        // Update best assignment if improved
        if (unsat_list.size() < best_unsat) {
            best_unsat = unsat_list.size();
            best_val = val;
        }
    }
    
    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        printf("%d ", best_val[i]);
    }
    printf("\n");
    
    return 0;
}