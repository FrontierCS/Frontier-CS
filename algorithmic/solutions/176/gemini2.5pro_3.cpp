#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <chrono>
#include <cmath>
#include <algorithm>

// Global variables
int n, m;
std::vector<std::vector<int>> clauses;
std::vector<std::vector<int>> pos_clauses;
std::vector<std::vector<int>> neg_clauses;

std::vector<int> assignment;
std::vector<int> best_assignment;
int best_satisfied_count;

std::vector<int> num_true_literals;
std::vector<int> unsatisfied_clauses_vec;
std::vector<int> where_in_unsat_vec;

std::mt19937 rng;

const double P_RANDOM_WALK = 0.4;
const int MAX_FLIPS_PER_TRY = 200000;

void read_input() {
    std::cin >> n >> m;
    clauses.resize(m, std::vector<int>(3));
    pos_clauses.resize(n + 1);
    neg_clauses.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int literal;
            std::cin >> literal;
            clauses[i][j] = literal;
            if (literal > 0) {
                pos_clauses[literal].push_back(i);
            } else {
                neg_clauses[-literal].push_back(i);
            }
        }
    }
}

void remove_from_unsat(int c_idx) {
    int pos_to_remove = where_in_unsat_vec[c_idx];
    int last_elem_c_idx = unsatisfied_clauses_vec.back();
    
    unsatisfied_clauses_vec[pos_to_remove] = last_elem_c_idx;
    where_in_unsat_vec[last_elem_c_idx] = pos_to_remove;
    
    unsatisfied_clauses_vec.pop_back();
}

void add_to_unsat(int c_idx) {
    where_in_unsat_vec[c_idx] = unsatisfied_clauses_vec.size();
    unsatisfied_clauses_vec.push_back(c_idx);
}

void flip(int v) {
    int old_val = assignment[v];
    assignment[v] = 1 - old_val;

    if (old_val == 0) { // Flipped 0 -> 1
        for (int c_idx : pos_clauses[v]) {
            if (num_true_literals[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            num_true_literals[c_idx]++;
        }
        for (int c_idx : neg_clauses[v]) {
            num_true_literals[c_idx]--;
            if (num_true_literals[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
    } else { // Flipped 1 -> 0
        for (int c_idx : pos_clauses[v]) {
            num_true_literals[c_idx]--;
            if (num_true_literals[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
        for (int c_idx : neg_clauses[v]) {
            if (num_true_literals[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            num_true_literals[c_idx]++;
        }
    }
}

int calculate_break_count(int v) {
    int break_count = 0;
    if (assignment[v] == 1) { // Will be flipped to 0
        for (int c_idx : pos_clauses[v]) {
            if (num_true_literals[c_idx] == 1) {
                break_count++;
            }
        }
    } else { // Will be flipped to 1
        for (int c_idx : neg_clauses[v]) {
            if (num_true_literals[c_idx] == 1) {
                break_count++;
            }
        }
    }
    return break_count;
}

void run_walksat() {
    // 1. Random initial assignment
    std::uniform_int_distribution<int> dist(0, 1);
    for (int i = 1; i <= n; ++i) {
        assignment[i] = dist(rng);
    }
    
    // 2. Initial calculation of satisfied/unsatisfied clauses
    num_true_literals.assign(m, 0);
    unsatisfied_clauses_vec.clear();
    for (int i = 0; i < m; ++i) {
        for (int literal : clauses[i]) {
            if (literal > 0) {
                if (assignment[literal] == 1) {
                    num_true_literals[i]++;
                }
            } else {
                if (assignment[-literal] == 0) {
                    num_true_literals[i]++;
                }
            }
        }
        if (num_true_literals[i] == 0) {
            add_to_unsat(i);
        }
    }
    
    int initial_satisfied = m - unsatisfied_clauses_vec.size();
    if (initial_satisfied > best_satisfied_count) {
        best_satisfied_count = initial_satisfied;
        best_assignment = assignment;
    }
    
    // 3. Main local search loop
    for (int flip_count = 0; flip_count < MAX_FLIPS_PER_TRY; ++flip_count) {
        if (unsatisfied_clauses_vec.empty()) {
            best_satisfied_count = m;
            best_assignment = assignment;
            return; 
        }
        
        // Pick an unsatisfied clause
        std::uniform_int_distribution<int> unsat_dist(0, unsatisfied_clauses_vec.size() - 1);
        int c_idx = unsatisfied_clauses_vec[unsat_dist(rng)];
        
        // Decide random walk or greedy
        std::uniform_real_distribution<double> real_dist(0.0, 1.0);
        if (real_dist(rng) < P_RANDOM_WALK) {
            // Random walk
            std::uniform_int_distribution<int> lit_dist(0, 2);
            int literal_to_flip = clauses[c_idx][lit_dist(rng)];
            flip(std::abs(literal_to_flip));
        } else {
            // Greedy move
            std::vector<int> vars_in_clause;
            for(int lit : clauses[c_idx]) {
                vars_in_clause.push_back(abs(lit));
            }
            std::sort(vars_in_clause.begin(), vars_in_clause.end());
            vars_in_clause.erase(std::unique(vars_in_clause.begin(), vars_in_clause.end()), vars_in_clause.end());

            int min_break_count = m + 1;
            std::vector<int> best_vars;
            
            for (int v : vars_in_clause) {
                int current_break_count = calculate_break_count(v);
                if (current_break_count < min_break_count) {
                    min_break_count = current_break_count;
                    best_vars.clear();
                    best_vars.push_back(v);
                } else if (current_break_count == min_break_count) {
                    best_vars.push_back(v);
                }
            }
            
            std::uniform_int_distribution<int> best_var_dist(0, best_vars.size() - 1);
            int best_var = best_vars[best_var_dist(rng)];
            flip(best_var);
        }
        
        int current_satisfied = m - unsatisfied_clauses_vec.size();
        if (current_satisfied > best_satisfied_count) {
            best_satisfied_count = current_satisfied;
            best_assignment = assignment;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    read_input();

    if (m == 0) {
        for (int i = 0; i < n; ++i) std::cout << "0 ";
        std::cout << "\n";
        return 0;
    }

    assignment.resize(n + 1);
    best_assignment.resize(n + 1);
    num_true_literals.resize(m);
    where_in_unsat_vec.resize(m);
    best_satisfied_count = -1;

    int num_tries = 0;
    while(num_tries < 10) {
        run_walksat();
        if (best_satisfied_count == m) break;
        num_tries++;
    }
    
    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}