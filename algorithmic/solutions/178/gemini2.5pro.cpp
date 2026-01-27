#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <chrono>
#include <array>
#include <algorithm>

int n, m;
std::vector<std::array<int, 3>> clauses;
std::vector<bool> best_assignment;
int max_satisfied_clauses = -1;

std::vector<std::vector<int>> clauses_with_var;
std::vector<std::vector<int>> clauses_with_neg_var;

std::mt19937 rng;

void add_to_unsat(int c_idx, std::vector<int>& u_clauses, std::vector<int>& where) {
    if (where[c_idx] == -1) {
        where[c_idx] = u_clauses.size();
        u_clauses.push_back(c_idx);
    }
}

void remove_from_unsat(int c_idx, std::vector<int>& u_clauses, std::vector<int>& where) {
    if (where[c_idx] != -1) {
        int pos = where[c_idx];
        int last_clause_idx = u_clauses.back();
        
        u_clauses[pos] = last_clause_idx;
        where[last_clause_idx] = pos;
        
        u_clauses.pop_back();
        where[c_idx] = -1;
    }
}

void walksat() {
    const double p = 0.5;
    const int MAX_RESTARTS = 30;
    const int MAX_FLIPS_PER_N = 2000;
    const int MAX_FLIPS = std::max(1, MAX_FLIPS_PER_N * n);

    clauses_with_var.assign(n + 1, std::vector<int>());
    clauses_with_neg_var.assign(n + 1, std::vector<int>());
    for (int i = 0; i < m; ++i) {
        for (int literal : clauses[i]) {
            if (literal > 0) {
                clauses_with_var[literal].push_back(i);
            } else {
                clauses_with_neg_var[-literal].push_back(i);
            }
        }
    }

    for (int restart = 0; restart < MAX_RESTARTS; ++restart) {
        std::vector<bool> current_assignment(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
        }

        std::vector<int> num_true_literals(m, 0);
        std::vector<int> unsatisfied_clauses_indices;
        std::vector<int> where_in_unsatisfied(m, -1);

        for (int i = 0; i < m; ++i) {
            for (int literal : clauses[i]) {
                int var = std::abs(literal);
                bool val = current_assignment[var];
                if (literal < 0) val = !val;
                if (val) {
                    num_true_literals[i]++;
                }
            }
            if (num_true_literals[i] == 0) {
                add_to_unsat(i, unsatisfied_clauses_indices, where_in_unsatisfied);
            }
        }
        
        int current_satisfied_count = m - unsatisfied_clauses_indices.size();
        if (current_satisfied_count > max_satisfied_clauses) {
            max_satisfied_clauses = current_satisfied_count;
            best_assignment = current_assignment;
            if (max_satisfied_clauses == m) return;
        }

        for (int flip = 0; flip < MAX_FLIPS; ++flip) {
            if (unsatisfied_clauses_indices.empty()) {
                break; 
            }

            int clause_idx = unsatisfied_clauses_indices[std::uniform_int_distribution<int>(0, unsatisfied_clauses_indices.size() - 1)(rng)];
            
            int var_to_flip = -1;

            if (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < p) {
                var_to_flip = std::abs(clauses[clause_idx][std::uniform_int_distribution<int>(0, 2)(rng)]);
            } else {
                std::vector<int> best_vars;
                int min_break_count = m + 1;
                
                for (int literal : clauses[clause_idx]) {
                    int var = std::abs(literal);
                    int break_count = 0;
                    if (current_assignment[var]) { // currently TRUE, would be flipped to FALSE
                        for (int affected_clause_idx : clauses_with_var[var]) {
                            if (num_true_literals[affected_clause_idx] == 1) {
                                break_count++;
                            }
                        }
                    } else { // currently FALSE, would be flipped to TRUE
                        for (int affected_clause_idx : clauses_with_neg_var[var]) {
                            if (num_true_literals[affected_clause_idx] == 1) {
                                break_count++;
                            }
                        }
                    }

                    if (break_count < min_break_count) {
                        min_break_count = break_count;
                        best_vars.clear();
                        best_vars.push_back(var);
                    } else if (break_count == min_break_count) {
                        best_vars.push_back(var);
                    }
                }
                var_to_flip = best_vars[std::uniform_int_distribution<int>(0, best_vars.size() - 1)(rng)];
            }
            
            current_assignment[var_to_flip] = !current_assignment[var_to_flip];

            if (current_assignment[var_to_flip]) { // Was FALSE, flipped to TRUE
                for (int c_idx : clauses_with_neg_var[var_to_flip]) {
                    num_true_literals[c_idx]--;
                    if (num_true_literals[c_idx] == 0) {
                        add_to_unsat(c_idx, unsatisfied_clauses_indices, where_in_unsatisfied);
                    }
                }
                for (int c_idx : clauses_with_var[var_to_flip]) {
                    bool was_unsat = (num_true_literals[c_idx] == 0);
                    num_true_literals[c_idx]++;
                    if (was_unsat) {
                        remove_from_unsat(c_idx, unsatisfied_clauses_indices, where_in_unsatisfied);
                    }
                }
            } else { // Was TRUE, flipped to FALSE
                for (int c_idx : clauses_with_var[var_to_flip]) {
                    num_true_literals[c_idx]--;
                    if (num_true_literals[c_idx] == 0) {
                        add_to_unsat(c_idx, unsatisfied_clauses_indices, where_in_unsatisfied);
                    }
                }
                for (int c_idx : clauses_with_neg_var[var_to_flip]) {
                    bool was_unsat = (num_true_literals[c_idx] == 0);
                    num_true_literals[c_idx]++;
                    if (was_unsat) {
                        remove_from_unsat(c_idx, unsatisfied_clauses_indices, where_in_unsatisfied);
                    }
                }
            }
            
            current_satisfied_count = m - unsatisfied_clauses_indices.size();
            if (current_satisfied_count > max_satisfied_clauses) {
                max_satisfied_clauses = current_satisfied_count;
                best_assignment = current_assignment;
                if (max_satisfied_clauses == m) return;
            }
        }
    }
}

void solve() {
    std::cin >> n >> m;
    clauses.resize(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }
    
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return;
    }
    
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    walksat();
    
    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}