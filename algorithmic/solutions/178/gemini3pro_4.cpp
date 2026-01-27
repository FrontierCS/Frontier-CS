#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

// Represents a clause with 3 literals
struct Clause {
    int l1, l2, l3;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> pos_occ; // Maps variable to list of clause indices where it appears positively
vector<vector<int>> neg_occ; // Maps variable to list of clause indices where it appears negatively
vector<int> assignment;      // Current assignment (1-based index)
vector<int> best_assignment; // Best assignment found so far
int current_sat_count;       // Current number of satisfied clauses
int max_sat_count = -1;
vector<int> clause_true_lits; // Number of true literals in each clause

// Efficient management of unsatisfied clauses
vector<int> unsat_clauses;
vector<int> clause_pos_in_unsat; 

// Add a clause to the unsatisfied set
void add_unsat(int c_idx) {
    if (clause_pos_in_unsat[c_idx] != -1) return;
    clause_pos_in_unsat[c_idx] = unsat_clauses.size();
    unsat_clauses.push_back(c_idx);
}

// Remove a clause from the unsatisfied set
void remove_unsat(int c_idx) {
    int pos = clause_pos_in_unsat[c_idx];
    if (pos == -1) return;
    int last_c = unsat_clauses.back();
    unsat_clauses[pos] = last_c;
    clause_pos_in_unsat[last_c] = pos;
    unsat_clauses.pop_back();
    clause_pos_in_unsat[c_idx] = -1;
}

// Full evaluation of the current assignment
void full_eval() {
    current_sat_count = 0;
    unsat_clauses.clear();
    fill(clause_pos_in_unsat.begin(), clause_pos_in_unsat.end(), -1);
    fill(clause_true_lits.begin(), clause_true_lits.end(), 0);

    for (int i = 0; i < m; ++i) {
        int sat = 0;
        int lits[3] = {clauses[i].l1, clauses[i].l2, clauses[i].l3};
        for (int val : lits) {
            // Check if literal evaluates to true
            bool is_true = (val > 0) ? (assignment[abs(val)] == 1) : (assignment[abs(val)] == 0);
            if (is_true) sat++;
        }
        clause_true_lits[i] = sat;
        if (sat > 0) {
            current_sat_count++;
        } else {
            add_unsat(i);
        }
    }
}

// Flip the value of variable v and update data structures
void flip(int v) {
    int old_val = assignment[v];
    int new_val = 1 - old_val;
    assignment[v] = new_val;

    // Clauses where v appeared with old_val (satisfied by v) now lose a true literal (the one corresponding to old_val)
    // Clauses where v appears with new_val (not satisfied by v previously) now gain a true literal
    const vector<int>& plus_list = (new_val == 1) ? pos_occ[v] : neg_occ[v];
    const vector<int>& minus_list = (new_val == 1) ? neg_occ[v] : pos_occ[v];

    for (int c_idx : plus_list) {
        if (clause_true_lits[c_idx] == 0) {
            current_sat_count++;
            remove_unsat(c_idx);
        }
        clause_true_lits[c_idx]++;
    }

    for (int c_idx : minus_list) {
        clause_true_lits[c_idx]--;
        if (clause_true_lits[c_idx] == 0) {
            current_sat_count--;
            add_unsat(c_idx);
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> n >> m)) return 0;

    pos_occ.resize(n + 1);
    neg_occ.resize(n + 1);
    clauses.resize(m);
    clause_true_lits.resize(m);
    clause_pos_in_unsat.resize(m, -1);
    assignment.resize(n + 1);
    best_assignment.resize(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        clauses[i] = {u, v, w};
        
        auto register_lit = [&](int lit, int c_idx) {
            if (lit > 0) pos_occ[lit].push_back(c_idx);
            else neg_occ[abs(lit)].push_back(c_idx);
        };
        register_lit(u, i);
        register_lit(v, i);
        register_lit(w, i);
    }

    // Initial Random Assignment
    for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
    full_eval();
    best_assignment = assignment;
    max_sat_count = current_sat_count;

    double time_limit = 0.95; // seconds (target < 1.0s)
    clock_t start_time = clock();
    long long iterations = 0;

    double p = 0.5; // WalkSAT noise probability
    
    // Main Local Search Loop (WalkSAT)
    while (true) {
        // Check time limit
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
        if (current_sat_count == m) break; // All satisfied
        if (unsat_clauses.empty()) break; 

        // Pick a random unsatisfied clause
        int r_idx = rand() % unsat_clauses.size();
        int c_idx = unsat_clauses[r_idx];

        int lits[3] = {clauses[c_idx].l1, clauses[c_idx].l2, clauses[c_idx].l3};
        int candidates[3] = {abs(lits[0]), abs(lits[1]), abs(lits[2])};
        
        struct VarInfo { int v; int broken; };
        VarInfo infos[3]; 

        bool found_zero_break = false;
        int zero_break_v = -1;

        // Evaluate flip impact for variables in the clause
        for (int i=0; i<3; ++i) {
            int v = candidates[i];
            int val = assignment[v]; 
            // Clauses currently satisfied by v (where v's literal is true)
            // If we flip v, these clauses lose a true literal. If count becomes 0, they break.
            const vector<int>& critical_clauses = (val == 1) ? pos_occ[v] : neg_occ[v];
            
            int broken = 0;
            for (int cc_idx : critical_clauses) {
                if (clause_true_lits[cc_idx] == 1) {
                    broken++;
                }
            }
            infos[i] = {v, broken};
            if (broken == 0) {
                found_zero_break = true;
                zero_break_v = v;
                break; 
            }
        }

        int flip_v = -1;
        
        if (found_zero_break) {
            flip_v = zero_break_v;
        } else {
            // WalkSAT strategy
            if ((double)rand() / RAND_MAX < p) {
                // Random walk: pick random variable from clause
                flip_v = candidates[rand() % 3];
            } else {
                // Greedy move (minimize broken clauses)
                int min_b = m + 1;
                for(int i=0; i<3; ++i) if(infos[i].broken < min_b) min_b = infos[i].broken;
                
                // Pick randomly among those with minimal break count
                int count = 0;
                for(int i=0; i<3; ++i) {
                    if(infos[i].broken == min_b) {
                        count++;
                        if (rand() % count == 0) flip_v = infos[i].v;
                    }
                }
            }
        }

        flip(flip_v);

        if (current_sat_count > max_sat_count) {
            max_sat_count = current_sat_count;
            best_assignment = assignment;
        }

        // Random restart logic to escape deep local optima
        iterations++;
        if (iterations % 50000 == 0) {
             for (int i = 1; i <= n; ++i) assignment[i] = rand() % 2;
             full_eval();
             if (current_sat_count > max_sat_count) {
                 max_sat_count = current_sat_count;
                 best_assignment = assignment;
             }
        }
    }

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}