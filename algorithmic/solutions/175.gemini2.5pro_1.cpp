#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <array>
#include <numeric>
#include <algorithm>
#include <chrono>

using namespace std;

// Problem parameters
int n, m;

// Clause representation
// Using pair<int, bool> for literal: {var_idx, sign}
// var_idx: 0 to n-1
// sign: true for positive (x), false for negative (¬x)
vector<array<pair<int, bool>, 3>> clauses;
vector<vector<int>> var_to_clauses;

// State for WalkSAT
vector<bool> current_assignment;
vector<int> sat_count;
vector<int> unsatisfied_clauses_indices;
vector<int> clause_idx_to_unsat_vec_idx;

// Best solution found
vector<bool> best_assignment;
int max_satisfied_clauses = -1;

// Random number generator
mt19937 rng;

// Helper to parse a literal from input format
void parse_literal(int raw_lit, pair<int, bool>& parsed_lit) {
    parsed_lit.first = abs(raw_lit) - 1;
    parsed_lit.second = raw_lit > 0;
}

// Helper to check if a literal is true under an assignment
inline bool is_literal_true(const pair<int, bool>& lit, const vector<bool>& assignment) {
    return assignment[lit.first] == lit.second;
}

// Initialize state for a WalkSAT run
void init_walksat() {
    current_assignment.resize(n);
    for (int i = 0; i < n; ++i) {
        current_assignment[i] = uniform_int_distribution<int>(0, 1)(rng);
    }
    
    sat_count.assign(m, 0);
    for (int i = 0; i < m; ++i) {
        for (const auto& lit : clauses[i]) {
            if (is_literal_true(lit, current_assignment)) {
                sat_count[i]++;
            }
        }
    }

    unsatisfied_clauses_indices.clear();
    clause_idx_to_unsat_vec_idx.assign(m, -1);
    for (int i = 0; i < m; ++i) {
        if (sat_count[i] == 0) {
            clause_idx_to_unsat_vec_idx[i] = unsatisfied_clauses_indices.size();
            unsatisfied_clauses_indices.push_back(i);
        }
    }
}

// Update the best solution found so far
void update_best_solution() {
    int satisfied_count = m - unsatisfied_clauses_indices.size();
    if (satisfied_count > max_satisfied_clauses) {
        max_satisfied_clauses = satisfied_count;
        best_assignment = current_assignment;
    }
}

// A single run of the WalkSAT algorithm
void walksat_run(int max_flips, int p_random_walk) {
    init_walksat();
    
    for (int flip = 0; flip < max_flips; ++flip) {
        if (unsatisfied_clauses_indices.empty()) {
            break;
        }

        // Pick a random unsatisfied clause
        int unsat_vec_idx = uniform_int_distribution<int>(0, unsatisfied_clauses_indices.size() - 1)(rng);
        int c_idx = unsatisfied_clauses_indices[unsat_vec_idx];

        int var_to_flip = -1;

        // With probability p_random_walk, choose a random variable from the clause
        if (uniform_int_distribution<int>(0, 99)(rng) < p_random_walk) {
            var_to_flip = clauses[c_idx][uniform_int_distribution<int>(0, 2)(rng)].first;
        } else {
            // Greedy step: choose variable that minimizes the break count
            int min_break_count = m + 2;
            vector<int> best_vars_to_flip;
            
            for (const auto& lit_to_make_true : clauses[c_idx]) {
                int var_idx = lit_to_make_true.first;
                int current_break_count = 0;
                for (int affected_c_idx : var_to_clauses[var_idx]) {
                    if (sat_count[affected_c_idx] == 1) {
                        for (const auto& lit : clauses[affected_c_idx]) {
                            if (lit.first == var_idx) {
                                if (is_literal_true(lit, current_assignment)) {
                                    current_break_count++;
                                }
                                break;
                            }
                        }
                    }
                }
                if (current_break_count < min_break_count) {
                    min_break_count = current_break_count;
                    best_vars_to_flip.clear();
                    best_vars_to_flip.push_back(var_idx);
                } else if (current_break_count == min_break_count) {
                    best_vars_to_flip.push_back(var_idx);
                }
            }
            var_to_flip = best_vars_to_flip[uniform_int_distribution<int>(0, best_vars_to_flip.size() - 1)(rng)];
        }

        // Flip the chosen variable
        bool old_val = current_assignment[var_to_flip];
        current_assignment[var_to_flip] = !old_val;

        // Update data structures for affected clauses
        for (int affected_c_idx : var_to_clauses[var_to_flip]) {
            for (const auto& lit : clauses[affected_c_idx]) {
                if (lit.first == var_to_flip) {
                    int old_sat_count = sat_count[affected_c_idx];
                    if (lit.second == old_val) { // this literal was true, now false
                        sat_count[affected_c_idx]--;
                    } else { // was false, now true
                        sat_count[affected_c_idx]++;
                    }
                    int new_sat_count = sat_count[affected_c_idx];

                    if (old_sat_count > 0 && new_sat_count == 0) {
                        // became unsatisfied
                        clause_idx_to_unsat_vec_idx[affected_c_idx] = unsatisfied_clauses_indices.size();
                        unsatisfied_clauses_indices.push_back(affected_c_idx);
                    } else if (old_sat_count == 0 && new_sat_count > 0) {
                        // became satisfied
                        int pos_in_unsat_vec = clause_idx_to_unsat_vec_idx[affected_c_idx];
                        int last_elem_c_idx = unsatisfied_clauses_indices.back();
                        
                        unsatisfied_clauses_indices[pos_in_unsat_vec] = last_elem_c_idx;
                        clause_idx_to_unsat_vec_idx[last_elem_c_idx] = pos_in_unsat_vec;

                        unsatisfied_clauses_indices.pop_back();
                        clause_idx_to_unsat_vec_idx[affected_c_idx] = -1;
                    }
                    break;
                }
            }
        }
    }
    update_best_solution();
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << "0" << (i == n - 1 ? "" : " ");
        }
        cout << endl;
        return 0;
    }

    clauses.resize(m);
    var_to_clauses.resize(n);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        parse_literal(a, clauses[i][0]);
        parse_literal(b, clauses[i][1]);
        parse_literal(c, clauses[i][2]);
        var_to_clauses[clauses[i][0].first].push_back(i);
        var_to_clauses[clauses[i][1].first].push_back(i);
        var_to_clauses[clauses[i][2].first].push_back(i);
    }

    // A variable can appear multiple times in a clause, remove duplicates in var_to_clauses
    for(int i=0; i<n; ++i) {
        sort(var_to_clauses[i].begin(), var_to_clauses[i].end());
        var_to_clauses[i].erase(unique(var_to_clauses[i].begin(), var_to_clauses[i].end()), var_to_clauses[i].end());
    }
    
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());
    
    best_assignment.assign(n, 0);
    
    // Time limit based restarts
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.9; // seconds

    while (true) {
        auto current_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit) {
            break;
        }
        walksat_run(4 * n, 30); // max_flips, p_random_walk (%)
        if (max_satisfied_clauses == m) break;
    }

    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}