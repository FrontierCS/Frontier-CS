#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

// Structure to represent a clause
struct Clause {
    int l[3]; // Literals: positive if x_i, negative if -x_i
};

int n, m;
vector<Clause> clauses;
// Adjacency list: which clauses contain which variable
vector<vector<int>> var_in_clauses;

// State
vector<int> assignment; // Current assignment (0 or 1)
vector<int> clause_sat_count; // Number of satisfied literals in each clause
vector<int> unsat_clauses; // List of indices of unsatisfied clauses
vector<int> unsat_map; // Map from clause index to position in unsat_clauses (-1 if satisfied)

// Best solution found
vector<int> best_assignment;
size_t best_unsat_count;

// Build the initial state (counts and unsat list) based on current assignment
void build_state() {
    fill(clause_sat_count.begin(), clause_sat_count.end(), 0);
    unsat_clauses.clear();
    fill(unsat_map.begin(), unsat_map.end(), -1);
    
    for (int i = 0; i < m; ++i) {
        int sat = 0;
        for (int j = 0; j < 3; ++j) {
            int lit = clauses[i].l[j];
            int v = abs(lit) - 1;
            bool is_pos = (lit > 0);
            if ((assignment[v] == 1) == is_pos) {
                sat++;
            }
        }
        clause_sat_count[i] = sat;
        if (sat == 0) {
            unsat_map[i] = unsat_clauses.size();
            unsat_clauses.push_back(i);
        }
    }
}

// Flip a variable and update state
void flip(int v) {
    int old_val = assignment[v];
    int new_val = 1 - old_val;
    assignment[v] = new_val;
    
    for (int c_idx : var_in_clauses[v]) {
        int delta = 0;
        // Calculate change in satisfied literal count for this clause
        for (int j = 0; j < 3; ++j) {
            int lit = clauses[c_idx].l[j];
            if (abs(lit) - 1 == v) {
                bool is_pos = (lit > 0);
                bool was_true = (old_val == 1) == is_pos;
                bool now_true = (new_val == 1) == is_pos;
                if (now_true && !was_true) delta++;
                if (!now_true && was_true) delta--;
            }
        }
        
        int old_sat = clause_sat_count[c_idx];
        clause_sat_count[c_idx] += delta;
        int new_sat = clause_sat_count[c_idx];
        
        // Update unsat list
        if (old_sat == 0 && new_sat > 0) {
            int pos = unsat_map[c_idx];
            int last_c = unsat_clauses.back();
            unsat_clauses[pos] = last_c;
            unsat_map[last_c] = pos;
            unsat_clauses.pop_back();
            unsat_map[c_idx] = -1;
        } else if (old_sat > 0 && new_sat == 0) {
            unsat_map[c_idx] = unsat_clauses.size();
            unsat_clauses.push_back(c_idx);
        }
    }
}

// Calculate how many satisfied clauses would become unsatisfied if v is flipped
int get_break_count(int v) {
    int break_count = 0;
    int old_val = assignment[v];
    int new_val = 1 - old_val;
    
    for (int c_idx : var_in_clauses[v]) {
        if (clause_sat_count[c_idx] == 0) continue; 
        
        int delta = 0;
        for (int j = 0; j < 3; ++j) {
            int lit = clauses[c_idx].l[j];
            if (abs(lit) - 1 == v) {
                bool is_pos = (lit > 0);
                bool was_true = (old_val == 1) == is_pos;
                bool now_true = (new_val == 1) == is_pos;
                if (now_true && !was_true) delta++;
                if (!now_true && was_true) delta--;
            }
        }
        
        if (clause_sat_count[c_idx] + delta == 0) {
            break_count++;
        }
    }
    return break_count;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(0));
    
    if (!(cin >> n >> m)) return 0;
    
    clauses.resize(m);
    var_in_clauses.resize(n);
    
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            cin >> clauses[i].l[j];
            int v = abs(clauses[i].l[j]) - 1;
            var_in_clauses[v].push_back(i);
        }
    }
    
    // Ensure unique clauses in adjacency list for efficiency
    for (int i = 0; i < n; ++i) {
        sort(var_in_clauses[i].begin(), var_in_clauses[i].end());
        var_in_clauses[i].erase(unique(var_in_clauses[i].begin(), var_in_clauses[i].end()), var_in_clauses[i].end());
    }
    
    assignment.resize(n);
    clause_sat_count.resize(m);
    unsat_map.resize(m);
    best_assignment.resize(n);
    
    fill(best_assignment.begin(), best_assignment.end(), 0);
    best_unsat_count = m + 1; // sentinel

    int max_tries = 200;
    int max_flips = 3000;
    clock_t start_time = clock();
    
    for (int t = 0; t < max_tries; ++t) {
        // Random Initialization
        for (int i = 0; i < n; ++i) assignment[i] = rand() % 2;
        build_state();
        
        if (unsat_clauses.size() < best_unsat_count) {
            best_unsat_count = unsat_clauses.size();
            best_assignment = assignment;
        }
        if (best_unsat_count == 0) break;
        
        for (int f = 0; f < max_flips; ++f) {
            if (unsat_clauses.empty()) break;
            
            // Pick a random unsatisfied clause
            int c_idx = unsat_clauses[rand() % unsat_clauses.size()];
            
            // Variables in this clause
            int vars[3];
            for(int k=0; k<3; ++k) vars[k] = abs(clauses[c_idx].l[k]) - 1;
            
            int flip_var = -1;
            
            // WalkSAT: Random walk with probability 0.4, else Greedy (min break count)
            if (rand() % 100 < 40) {
                flip_var = vars[rand() % 3];
            } else {
                int min_break = 1e9;
                vector<int> candidates;
                for (int k = 0; k < 3; ++k) {
                    int v = vars[k];
                    // Skip duplicates in same clause
                    bool distinct = true;
                    for(int z=0; z<k; ++z) if(vars[z] == v) distinct = false;
                    if(!distinct) continue;

                    int b = get_break_count(v);
                    if (b < min_break) {
                        min_break = b;
                        candidates.clear();
                        candidates.push_back(v);
                    } else if (b == min_break) {
                        candidates.push_back(v);
                    }
                }
                if (!candidates.empty())
                    flip_var = candidates[rand() % candidates.size()];
                else
                    flip_var = vars[rand() % 3];
            }
            
            flip(flip_var);
            
            if (unsat_clauses.size() < best_unsat_count) {
                best_unsat_count = unsat_clauses.size();
                best_assignment = assignment;
                if (best_unsat_count == 0) goto end_search;
            }
        }
        
        // Time safety check (approx 0.95 seconds)
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 0.95) break;
    }
    
    end_search:;
    
    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;
    
    return 0;
}