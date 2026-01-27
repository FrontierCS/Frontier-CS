#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

struct Clause {
    vector<int> literals;
    int id;
};

int n, m;
vector<Clause> clauses;
vector<vector<pair<int, int>>> occ; // var -> list of (clause_index, literal)
vector<int> assignment;
vector<int> best_assignment;
vector<int> sat_count;
vector<int> unsat_clauses;
vector<int> pos_in_unsat;
int best_sat = -1;

inline bool is_lit_true(int lit, int val) {
    // If lit > 0, it's variable v. True if val==1.
    // If lit < 0, it's NOT v. True if val==0.
    // (lit > 0) is true for pos, false for neg.
    // (val == 1) is true for 1, false for 0.
    // XNOR logic: same truth value means satisfied.
    return (lit > 0) == (val == 1);
}

void add_unsat(int c_idx) {
    if (pos_in_unsat[c_idx] != -1) return;
    pos_in_unsat[c_idx] = unsat_clauses.size();
    unsat_clauses.push_back(c_idx);
}

void remove_unsat(int c_idx) {
    int pos = pos_in_unsat[c_idx];
    if (pos == -1) return;
    
    int last_c = unsat_clauses.back();
    unsat_clauses[pos] = last_c;
    pos_in_unsat[last_c] = pos;
    
    unsat_clauses.pop_back();
    pos_in_unsat[c_idx] = -1;
}

void init_assignment() {
    unsat_clauses.clear();
    fill(pos_in_unsat.begin(), pos_in_unsat.end(), -1);
    fill(sat_count.begin(), sat_count.end(), 0);
    
    for (int i = 1; i <= n; ++i) {
        assignment[i] = rand() % 2;
    }
    
    for (int i = 0; i < clauses.size(); ++i) {
        for (int lit : clauses[i].literals) {
            if (is_lit_true(lit, assignment[abs(lit)])) {
                sat_count[i]++;
            }
        }
        if (sat_count[i] == 0) {
            add_unsat(i);
        }
    }
    
    int current_sat = (int)clauses.size() - (int)unsat_clauses.size();
    if (current_sat > best_sat) {
        best_sat = current_sat;
        best_assignment = assignment;
    }
}

void flip(int var) {
    int old_val = assignment[var];
    int new_val = 1 - old_val;
    assignment[var] = new_val;
    
    for (auto& p : occ[var]) {
        int c_idx = p.first;
        int lit = p.second;
        
        bool was_true = is_lit_true(lit, old_val);
        
        if (was_true) {
            // It was true, now false.
            sat_count[c_idx]--;
            if (sat_count[c_idx] == 0) {
                add_unsat(c_idx);
            }
        } else {
            // It was false, now true.
            if (sat_count[c_idx] == 0) {
                remove_unsat(c_idx);
            }
            sat_count[c_idx]++;
        }
    }
}

int main() {
    fast_io();
    srand(time(NULL));

    if (!(cin >> n >> m)) return 0;

    int always_sat_cnt = 0;
    for (int i = 0; i < m; ++i) {
        int l1, l2, l3;
        cin >> l1 >> l2 >> l3;
        vector<int> lits = {l1, l2, l3};
        // Simplify clause: sort and unique
        sort(lits.begin(), lits.end(), [](int a, int b){ return abs(a) < abs(b); });
        lits.erase(unique(lits.begin(), lits.end()), lits.end());
        
        bool tautology = false;
        for (size_t j = 0; j + 1 < lits.size(); ++j) {
            if (abs(lits[j]) == abs(lits[j+1])) {
                // Same variable, different sign (since duplicates removed)
                tautology = true;
                break;
            }
        }
        
        if (!tautology) {
            clauses.push_back({lits, (int)clauses.size()});
        } else {
            always_sat_cnt++;
        }
    }

    // Build occurrence lists
    occ.assign(n + 1, {});
    for (int i = 0; i < clauses.size(); ++i) {
        for (int lit : clauses[i].literals) {
            occ[abs(lit)].push_back({i, lit});
        }
    }
    
    sat_count.resize(clauses.size());
    pos_in_unsat.assign(clauses.size(), -1);
    assignment.resize(n + 1);
    best_assignment.resize(n + 1);
    
    // Fallback if no active clauses
    if (clauses.empty()) {
        for (int i = 1; i <= n; ++i) cout << (i==1?"":" ") << 0;
        cout << "\n";
        return 0;
    }

    clock_t start_time = clock();
    // Using slightly less than 1.0s to stay safe.
    double time_limit = 0.95; 
    
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        init_assignment();
        
        if (unsat_clauses.empty()) break;

        // WalkSAT iterations
        int max_flips = 30000; 
        for (int f = 0; f < max_flips; ++f) {
            if (unsat_clauses.empty()) {
                best_assignment = assignment;
                goto done;
            }

            int c_unsat = unsat_clauses[rand() % unsat_clauses.size()];
            const auto& lits = clauses[c_unsat].literals;
            
            // With probability ~50%, pick random variable from clause.
            // Otherwise, pick variable that minimizes breaks (greedy).
            bool random_move = (rand() & 1);
            
            int best_var = -1;
            
            if (random_move) {
                best_var = abs(lits[rand() % lits.size()]);
            } else {
                int min_breaks = 1e9;
                vector<int> candidates;
                
                for (int lit : lits) {
                    int var = abs(lit);
                    int breaks = 0;
                    // Calculate breaks
                    for (auto& p : occ[var]) {
                        int c_idx = p.first;
                        int l_val = p.second;
                        // A clause breaks if it is currently satisfied, 
                        // has exactly 1 true literal, and that literal is the one corresponding to var.
                        if (sat_count[c_idx] == 1 && is_lit_true(l_val, assignment[var])) {
                            breaks++;
                        }
                    }
                    if (breaks < min_breaks) {
                        min_breaks = breaks;
                        candidates.clear();
                        candidates.push_back(var);
                    } else if (breaks == min_breaks) {
                        candidates.push_back(var);
                    }
                }
                if (!candidates.empty()) {
                    best_var = candidates[rand() % candidates.size()];
                } else {
                    best_var = abs(lits[rand() % lits.size()]);
                }
            }
            
            flip(best_var);
            
            if ((int)clauses.size() - (int)unsat_clauses.size() > best_sat) {
                best_sat = (int)clauses.size() - (int)unsat_clauses.size();
                best_assignment = assignment;
            }
        }
    }

done:
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}