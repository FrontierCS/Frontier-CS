#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>

// Global variables to hold problem data
int n, m;
std::vector<std::vector<int>> clauses;
std::vector<std::vector<int>> clauses_of_var; // indices of clauses where var appears positively
std::vector<std::vector<int>> neg_clauses_of_var; // indices of clauses where var appears negatively

// PRNG
std::mt19937 rng;

void read_input() {
    std::cin >> n >> m;
    clauses.resize(m, std::vector<int>(3));
    clauses_of_var.resize(n + 1);
    neg_clauses_of_var.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            std::cin >> clauses[i][j];
            int var = std::abs(clauses[i][j]);
            if (clauses[i][j] > 0) {
                clauses_of_var[var].push_back(i);
            } else {
                neg_clauses_of_var[var].push_back(i);
            }
        }
    }
}

// Helper to evaluate a literal given an assignment
bool is_true(int literal, const std::vector<bool>& assignment) {
    if (literal > 0) {
        return assignment[literal];
    }
    return !assignment[-literal];
}

void solve() {
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return;
    }

    // Seed RNG
    rng.seed(std::random_device{}());

    std::vector<bool> best_assignment(n + 1);
    int max_satisfied = -1;

    const int NUM_RESTARTS = 30;
    const int MAX_FLIPS = 100 * n;
    const double p_random_walk = 0.5;

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        std::vector<bool> current_assignment(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
        }

        std::vector<int> num_true_literals(m);
        std::vector<int> unsatisfied_clauses;
        std::vector<int> where_in_unsat(m, -1);

        for (int i = 0; i < m; ++i) {
            int count = 0;
            for (int literal : clauses[i]) {
                if (is_true(literal, current_assignment)) {
                    count++;
                }
            }
            num_true_literals[i] = count;
            if (count == 0) {
                where_in_unsat[i] = unsatisfied_clauses.size();
                unsatisfied_clauses.push_back(i);
            }
        }
        
        int current_satisfied = m - unsatisfied_clauses.size();
        if (current_satisfied > max_satisfied) {
            max_satisfied = current_satisfied;
            best_assignment = current_assignment;
            if (max_satisfied == m) break;
        }

        for (int flip = 0; flip < MAX_FLIPS; ++flip) {
            if (unsatisfied_clauses.empty()) {
                break;
            }

            int c_idx = unsatisfied_clauses[std::uniform_int_distribution<int>(0, unsatisfied_clauses.size() - 1)(rng)];

            int var_to_flip = -1;
            
            std::uniform_real_distribution<double> dist(0.0, 1.0);
            if (dist(rng) < p_random_walk) {
                var_to_flip = std::abs(clauses[c_idx][std::uniform_int_distribution<int>(0, 2)(rng)]);
            } else {
                int min_break_count = m + 1;
                std::vector<int> best_vars;

                std::vector<int> vars_in_clause;
                for(int lit : clauses[c_idx]) {
                    vars_in_clause.push_back(std::abs(lit));
                }
                std::sort(vars_in_clause.begin(), vars_in_clause.end());
                vars_in_clause.erase(std::unique(vars_in_clause.begin(), vars_in_clause.end()), vars_in_clause.end());

                for (int var : vars_in_clause) {
                    int break_count = 0;
                    if (current_assignment[var]) { // flipping 1 to 0
                        for (int affected_c : clauses_of_var[var]) {
                            if (num_true_literals[affected_c] == 1) {
                                break_count++;
                            }
                        }
                    } else { // flipping 0 to 1
                         for (int affected_c : neg_clauses_of_var[var]) {
                            if (num_true_literals[affected_c] == 1) {
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
            
            bool old_val = current_assignment[var_to_flip];
            current_assignment[var_to_flip] = !old_val;

            auto update_clauses = [&](const std::vector<int>& affected_clauses, bool val_increase) {
                for (int affected_c : affected_clauses) {
                    int old_num_true = num_true_literals[affected_c];
                    if (val_increase) num_true_literals[affected_c]++;
                    else num_true_literals[affected_c]--;
                    int new_num_true = num_true_literals[affected_c];

                    if (old_num_true == 0 && new_num_true > 0) { // became satisfied
                        int idx_in_unsat = where_in_unsat[affected_c];
                        int last_c_idx = unsatisfied_clauses.back();
                        unsatisfied_clauses[idx_in_unsat] = last_c_idx;
                        where_in_unsat[last_c_idx] = idx_in_unsat;
                        unsatisfied_clauses.pop_back();
                        where_in_unsat[affected_c] = -1;
                    } else if (old_num_true > 0 && new_num_true == 0) { // became unsatisfied
                        where_in_unsat[affected_c] = unsatisfied_clauses.size();
                        unsatisfied_clauses.push_back(affected_c);
                    }
                }
            };
            
            if (old_val) { // 1 -> 0
                update_clauses(clauses_of_var[var_to_flip], false);
                update_clauses(neg_clauses_of_var[var_to_flip], true);
            } else { // 0 -> 1
                update_clauses(clauses_of_var[var_to_flip], true);
                update_clauses(neg_clauses_of_var[var_to_flip], false);
            }
            
            current_satisfied = m - unsatisfied_clauses.size();
            if (current_satisfied > max_satisfied) {
                max_satisfied = current_satisfied;
                best_assignment = current_assignment;
                if (max_satisfied == m) break;
            }
        }
        if (max_satisfied == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    read_input();
    solve();
    return 0;
}