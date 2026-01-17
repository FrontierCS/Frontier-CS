#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <chrono>
#include <algorithm>

// Random number generation
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

int n, m;
std::vector<std::vector<int>> clauses;
std::vector<bool> best_assignment;
int max_satisfied_clauses = -1;

// Data structures for WalkSAT
std::vector<bool> assignment;
std::vector<int> num_true_literals;
std::vector<int> unsatisfied_clauses_indices;
std::vector<int> pos_in_unsat;
std::vector<std::vector<int>> clauses_with_pos_var;
std::vector<std::vector<int>> clauses_with_neg_var;

// Helper to evaluate a literal based on the current assignment
inline bool is_true(int literal) {
    if (literal > 0) {
        return assignment[literal];
    }
    return !assignment[-literal];
}

// Function to flip a variable and update data structures
void flip(int var_to_flip) {
    bool old_val = assignment[var_to_flip];
    assignment[var_to_flip] = !old_val;

    if (!old_val) { // Flipped from 0 to 1
        // Positive occurrences of var_to_flip now become true
        for (int clause_idx : clauses_with_pos_var[var_to_flip]) {
            if (num_true_literals[clause_idx] == 0) { // Clause becomes satisfied
                int pos = pos_in_unsat[clause_idx];
                int last_clause_idx = unsatisfied_clauses_indices.back();
                unsatisfied_clauses_indices[pos] = last_clause_idx;
                pos_in_unsat[last_clause_idx] = pos;
                unsatisfied_clauses_indices.pop_back();
                pos_in_unsat[clause_idx] = -1;
            }
            num_true_literals[clause_idx]++;
        }
        // Negative occurrences of var_to_flip now become false
        for (int clause_idx : clauses_with_neg_var[var_to_flip]) {
            num_true_literals[clause_idx]--;
            if (num_true_literals[clause_idx] == 0) { // Clause becomes unsatisfied
                pos_in_unsat[clause_idx] = unsatisfied_clauses_indices.size();
                unsatisfied_clauses_indices.push_back(clause_idx);
            }
        }
    } else { // Flipped from 1 to 0
        // Positive occurrences of var_to_flip now become false
        for (int clause_idx : clauses_with_pos_var[var_to_flip]) {
            num_true_literals[clause_idx]--;
            if (num_true_literals[clause_idx] == 0) { // Clause becomes unsatisfied
                pos_in_unsat[clause_idx] = unsatisfied_clauses_indices.size();
                unsatisfied_clauses_indices.push_back(clause_idx);
            }
        }
        // Negative occurrences of var_to_flip now become true
        for (int clause_idx : clauses_with_neg_var[var_to_flip]) {
            if (num_true_literals[clause_idx] == 0) { // Clause becomes satisfied
                int pos = pos_in_unsat[clause_idx];
                int last_clause_idx = unsatisfied_clauses_indices.back();
                unsatisfied_clauses_indices[pos] = last_clause_idx;
                pos_in_unsat[last_clause_idx] = pos;
                unsatisfied_clauses_indices.pop_back();
                pos_in_unsat[clause_idx] = -1;
            }
            num_true_literals[clause_idx]++;
        }
    }
}

void solve() {
    auto start_time = std::chrono::steady_clock::now();
    
    clauses_with_pos_var.assign(n + 1, std::vector<int>());
    clauses_with_neg_var.assign(n + 1, std::vector<int>());
    for (int i = 0; i < m; ++i) {
        for (int literal : clauses[i]) {
            if (literal > 0) {
                clauses_with_pos_var[literal].push_back(i);
            } else {
                clauses_with_neg_var[-literal].push_back(i);
            }
        }
    }

    // Loop with restarts until time limit is reached
    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > 1.9) {
            break;
        }

        // Initialize a new run with a random assignment
        assignment.assign(n + 1, false);
        for (int i = 1; i <= n; ++i) {
            assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
        }

        num_true_literals.assign(m, 0);
        unsatisfied_clauses_indices.clear();
        pos_in_unsat.assign(m, -1);
        
        for (int i = 0; i < m; ++i) {
            for (int literal : clauses[i]) {
                if (is_true(literal)) {
                    num_true_literals[i]++;
                }
            }
            if (num_true_literals[i] == 0) {
                pos_in_unsat[i] = unsatisfied_clauses_indices.size();
                unsatisfied_clauses_indices.push_back(i);
            }
        }
        
        int current_satisfied = m - unsatisfied_clauses_indices.size();
        if (current_satisfied > max_satisfied_clauses) {
            max_satisfied_clauses = current_satisfied;
            best_assignment = assignment;
        }

        // WalkSAT inner loop
        const int max_flips_per_run = 200000;
        for (int flip_count = 0; flip_count < max_flips_per_run; ++flip_count) {
            if (unsatisfied_clauses_indices.empty()) {
                max_satisfied_clauses = m;
                best_assignment = assignment;
                return; // Found a satisfying assignment
            }

            int clause_idx = unsatisfied_clauses_indices[std::uniform_int_distribution<int>(0, unsatisfied_clauses_indices.size() - 1)(rng)];
            
            std::vector<int> vars_in_clause;
            for (int literal : clauses[clause_idx]) {
                vars_in_clause.push_back(std::abs(literal));
            }
            std::sort(vars_in_clause.begin(), vars_in_clause.end());
            vars_in_clause.erase(std::unique(vars_in_clause.begin(), vars_in_clause.end()), vars_in_clause.end());

            const double p = 0.5;
            if (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < p) { // Random walk
                int var_to_flip = vars_in_clause[std::uniform_int_distribution<int>(0, vars_in_clause.size() - 1)(rng)];
                flip(var_to_flip);
            } else { // Greedy move
                int min_break_count = m + 1;
                std::vector<int> best_vars;
                
                for (int var : vars_in_clause) {
                    int break_count = 0;
                    if (assignment[var]) { // if var is true, flipping it makes literal 'var' false
                        for (int affected_clause_idx : clauses_with_pos_var[var]) {
                            if (num_true_literals[affected_clause_idx] == 1) {
                                break_count++;
                            }
                        }
                    } else { // if var is false, flipping it makes literal '-var' false
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
                int var_to_flip = best_vars[std::uniform_int_distribution<int>(0, best_vars.size() - 1)(rng)];
                flip(var_to_flip);
            }
            
            current_satisfied = m - unsatisfied_clauses_indices.size();
            if (current_satisfied > max_satisfied_clauses) {
                max_satisfied_clauses = current_satisfied;
                best_assignment = assignment;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return 0;
    }

    clauses.resize(m, std::vector<int>(3));
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }

    // Start with a random assignment as a baseline
    best_assignment.assign(n + 1, false);
    for (int i = 1; i <= n; ++i) {
        best_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
    }
    
    int initial_satisfied = 0;
    for (const auto& clause : clauses) {
        bool satisfied = false;
        for (int literal : clause) {
            if (literal > 0) {
                if (best_assignment[literal]) {
                    satisfied = true;
                    break;
                }
            } else {
                if (!best_assignment[-literal]) {
                    satisfied = true;
                    break;
                }
            }
        }
        if (satisfied) initial_satisfied++;
    }
    max_satisfied_clauses = initial_satisfied;

    solve();

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}