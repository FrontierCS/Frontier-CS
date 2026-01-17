#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <array>

// Helper function to evaluate a literal given an assignment
bool is_true(int literal, const std::vector<int>& assignment) {
    if (literal > 0) {
        return assignment[literal] == 1;
    } else {
        return assignment[-literal] == 0;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "1" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return 0;
    }

    std::vector<std::array<int, 3>> clauses(m);
    std::vector<std::vector<int>> var_to_clauses(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v, w;
        std::cin >> u >> v >> w;
        clauses[i] = {u, v, w};
        var_to_clauses[std::abs(u)].push_back(i);
        var_to_clauses[std::abs(v)].push_back(i);
        var_to_clauses[std::abs(w)].push_back(i);
    }

    for (int i = 1; i <= n; ++i) {
        std::sort(var_to_clauses[i].begin(), var_to_clauses[i].end());
        var_to_clauses[i].erase(std::unique(var_to_clauses[i].begin(), var_to_clauses[i].end()), var_to_clauses[i].end());
    }
    
    std::mt19937 gen(std::random_device{}());
    
    std::vector<int> best_assignment(n + 1);
    int min_unsatisfied_count = m + 1;

    int num_restarts = 5;
    for (int restart = 0; restart < num_restarts; ++restart) {
        std::vector<int> assignment(n + 1);
        std::uniform_int_distribution<> distrib_bool(0, 1);
        for (int i = 1; i <= n; ++i) {
            assignment[i] = distrib_bool(gen);
        }

        std::vector<int> sat_counts(m, 0);
        std::vector<int> unsatisfied_clauses_indices;
        std::vector<int> where_in_unsat(m, -1);
        
        for (int i = 0; i < m; ++i) {
            for (int literal : clauses[i]) {
                if (is_true(literal, assignment)) {
                    sat_counts[i]++;
                }
            }
            if (sat_counts[i] == 0) {
                where_in_unsat[i] = unsatisfied_clauses_indices.size();
                unsatisfied_clauses_indices.push_back(i);
            }
        }
        
        int max_flips = 200000;
        
        for (int flip = 0; flip < max_flips; ++flip) {
            if (unsatisfied_clauses_indices.size() < min_unsatisfied_count) {
                min_unsatisfied_count = unsatisfied_clauses_indices.size();
                best_assignment = assignment;
                if (min_unsatisfied_count == 0) break;
            }
            if (unsatisfied_clauses_indices.empty()) break;
            
            std::uniform_int_distribution<> distrib_unsat(0, unsatisfied_clauses_indices.size() - 1);
            int clause_to_fix_idx = unsatisfied_clauses_indices[distrib_unsat(gen)];
            
            int var_to_flip = -1;

            std::uniform_real_distribution<> distrib_p(0.0, 1.0);
            if (distrib_p(gen) < 0.4) {
                std::uniform_int_distribution<> distrib_lit(0, 2);
                var_to_flip = std::abs(clauses[clause_to_fix_idx][distrib_lit(gen)]);
            } else {
                int min_break_count = m + 1;
                std::vector<int> best_vars;
                
                std::vector<int> unique_vars;
                for(int lit : clauses[clause_to_fix_idx]) unique_vars.push_back(std::abs(lit));
                std::sort(unique_vars.begin(), unique_vars.end());
                unique_vars.erase(std::unique(unique_vars.begin(), unique_vars.end()), unique_vars.end());

                for (int var : unique_vars) {
                    int current_break_count = 0;
                    for (int affected_clause_idx : var_to_clauses[var]) {
                        if (sat_counts[affected_clause_idx] == 1) {
                            for (int affected_lit : clauses[affected_clause_idx]) {
                                if (std::abs(affected_lit) == var && is_true(affected_lit, assignment)) {
                                    current_break_count++;
                                    break;
                                }
                            }
                        }
                    }

                    if (current_break_count < min_break_count) {
                        min_break_count = current_break_count;
                        best_vars.clear();
                        best_vars.push_back(var);
                    } else if (current_break_count == min_break_count) {
                        best_vars.push_back(var);
                    }
                }
                
                std::uniform_int_distribution<> distrib_best(0, best_vars.size() - 1);
                var_to_flip = best_vars[distrib_best(gen)];
            }

            assignment[var_to_flip] = 1 - assignment[var_to_flip];

            for (int affected_clause_idx : var_to_clauses[var_to_flip]) {
                int old_sat_count = sat_counts[affected_clause_idx];
                
                int new_sat_count = 0;
                for (int literal : clauses[affected_clause_idx]) {
                    if (is_true(literal, assignment)) {
                        new_sat_count++;
                    }
                }
                sat_counts[affected_clause_idx] = new_sat_count;
                
                if (old_sat_count > 0 && new_sat_count == 0) {
                    where_in_unsat[affected_clause_idx] = unsatisfied_clauses_indices.size();
                    unsatisfied_clauses_indices.push_back(affected_clause_idx);
                } else if (old_sat_count == 0 && new_sat_count > 0) {
                    int pos = where_in_unsat[affected_clause_idx];
                    int back_idx = unsatisfied_clauses_indices.back();
                    
                    unsatisfied_clauses_indices[pos] = back_idx;
                    where_in_unsat[back_idx] = pos;
                    
                    unsatisfied_clauses_indices.pop_back();
                    where_in_unsat[affected_clause_idx] = -1;
                }
            }
        }
        if (min_unsatisfied_count == 0) break;
    }
    
    if (min_unsatisfied_count == m + 1) {
        std::uniform_int_distribution<> distrib_bool(0, 1);
        for (int i = 1; i <= n; ++i) {
            best_assignment[i] = distrib_bool(gen);
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}