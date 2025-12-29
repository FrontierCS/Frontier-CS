#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <array>
#include <chrono>
#include <algorithm>
#include <cmath>

// Random number generation
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

// Problem parameters
int n, m;
std::vector<std::array<int, 3>> clauses;
std::vector<std::vector<int>> literal_to_clauses;

// State for local search
std::vector<bool> current_assignment;
std::vector<int> sat_count;
std::vector<int> unsat_clauses;
std::vector<int> unsat_pos;

// Best solution found
std::vector<bool> best_assignment;
int min_unsat_count;

// Convert literal to index for our adjacency list: v -> 2*(v-1)+1, -v -> 2*(v-1)
int literal_to_idx(int literal) {
    if (literal > 0) return 2 * (literal - 1) + 1;
    return 2 * (-literal - 1);
}

// Check if a literal is true under the current assignment
bool is_true(int literal) {
    if (literal > 0) return current_assignment[literal - 1];
    return !current_assignment[-literal - 1];
}

void init_state_with_random_assignment() {
    current_assignment.assign(n, false);
    for (int i = 0; i < n; ++i) {
        current_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
    }

    sat_count.assign(m, 0);
    unsat_clauses.clear();
    unsat_pos.assign(m, -1);

    for (int i = 0; i < m; ++i) {
        for (int literal : clauses[i]) {
            if (is_true(literal)) {
                sat_count[i]++;
            }
        }
        if (sat_count[i] == 0) {
            unsat_pos[i] = unsat_clauses.size();
            unsat_clauses.push_back(i);
        }
    }
    
    if (unsat_clauses.size() < min_unsat_count) {
        min_unsat_count = unsat_clauses.size();
        best_assignment = current_assignment;
    }
}

void flip_variable(int var_idx) {
    bool old_val = current_assignment[var_idx];
    current_assignment[var_idx] = !old_val;
    
    int pos_lit_idx = 2 * var_idx + 1;
    int neg_lit_idx = 2 * var_idx;

    if (!old_val) { // Was FALSE, now TRUE
        for (int clause_idx : literal_to_clauses[pos_lit_idx]) {
            if (++sat_count[clause_idx] == 1) { // Became satisfied
                int pos = unsat_pos[clause_idx];
                int last_clause_idx = unsat_clauses.back();
                unsat_clauses[pos] = last_clause_idx;
                unsat_pos[last_clause_idx] = pos;
                unsat_clauses.pop_back();
                unsat_pos[clause_idx] = -1;
            }
        }
        for (int clause_idx : literal_to_clauses[neg_lit_idx]) {
            if (--sat_count[clause_idx] == 0) { // Became unsatisfied
                unsat_pos[clause_idx] = unsat_clauses.size();
                unsat_clauses.push_back(clause_idx);
            }
        }
    } 
    else { // Was TRUE, now FALSE
        for (int clause_idx : literal_to_clauses[pos_lit_idx]) {
            if (--sat_count[clause_idx] == 0) { // Became unsatisfied
                unsat_pos[clause_idx] = unsat_clauses.size();
                unsat_clauses.push_back(clause_idx);
            }
        }
        for (int clause_idx : literal_to_clauses[neg_lit_idx]) {
            if (++sat_count[clause_idx] == 1) { // Became satisfied
                int pos = unsat_pos[clause_idx];
                int last_clause_idx = unsat_clauses.back();
                unsat_clauses[pos] = last_clause_idx;
                unsat_pos[last_clause_idx] = pos;
                unsat_clauses.pop_back();
                unsat_pos[clause_idx] = -1;
            }
        }
    }
}

int count_break(int var_idx) {
    int break_count = 0;
    bool current_val = current_assignment[var_idx];
    int breaking_lit_idx = current_val ? 2 * var_idx + 1 : 2 * var_idx;
    
    for (int clause_idx : literal_to_clauses[breaking_lit_idx]) {
        if (sat_count[clause_idx] == 1) {
            break_count++;
        }
    }
    return break_count;
}

void solve() {
    auto start_time = std::chrono::steady_clock::now();
    double time_limit = 2.9;

    min_unsat_count = m + 1;

    int max_tries = 100;
    for(int t=0; t<max_tries; ++t) {
        if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start_time).count() > time_limit) break;

        init_state_with_random_assignment();
        if (min_unsat_count == 0) break;

        int max_flips = 300000;
        for (int flip_iter = 0; flip_iter < max_flips; ++flip_iter) {
            if (unsat_clauses.empty()) break;
            
            if ((flip_iter & 63) == 0) {
                if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start_time).count() > time_limit) {
                    t = max_tries;
                    break;
                }
            }

            int clause_idx = unsat_clauses[std::uniform_int_distribution<int>(0, unsat_clauses.size() - 1)(rng)];
            
            int best_var_to_flip = -1;
            
            double p = 0.4;
            if (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < p) {
                int random_lit_idx_in_clause = std::uniform_int_distribution<int>(0, 2)(rng);
                int literal = clauses[clause_idx][random_lit_idx_in_clause];
                best_var_to_flip = std::abs(literal) - 1;
            } else {
                int min_break = m + 1;
                std::vector<int> best_vars;
                best_vars.reserve(3);
                for (int literal : clauses[clause_idx]) {
                    int var_idx = std::abs(literal) - 1;
                    int current_break = count_break(var_idx);
                    if (current_break < min_break) {
                        min_break = current_break;
                        best_vars.clear();
                        best_vars.push_back(var_idx);
                    } else if (current_break == min_break) {
                        best_vars.push_back(var_idx);
                    }
                }
                best_var_to_flip = best_vars[std::uniform_int_distribution<int>(0, best_vars.size() - 1)(rng)];
            }
            
            flip_variable(best_var_to_flip);
            
            if (unsat_clauses.size() < min_unsat_count) {
                min_unsat_count = unsat_clauses.size();
                best_assignment = current_assignment;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    clauses.resize(m);
    literal_to_clauses.resize(2 * n);

    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            std::cin >> clauses[i][j];
            literal_to_clauses[literal_to_idx(clauses[i][j])].push_back(i);
        }
    }
    
    best_assignment.assign(n, false);

    if (m > 0) {
        solve();
    } else {
        // Any assignment is fine for m=0, all zero is a deterministic one.
    }

    for (int i = 0; i < n; ++i) {
        std::cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}