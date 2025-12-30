#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <algorithm>
#include <array>

// Problem state
int n, m;
std::vector<std::array<int, 3>> clauses;
std::vector<std::vector<int>> pos_occurs, neg_occurs;

// WalkSAT state
std::vector<int> assignment;
std::vector<int> best_assignment;
int min_unsatisfied_count;

std::vector<int> num_true_literals;
std::vector<int> unsatisfied_clauses_indices;
std::vector<int> where_in_unsat;

std::mt19937 rng;
const double P_NOISE = 0.3;

void read_input() {
    std::cin >> n >> m;
    clauses.resize(m);
    pos_occurs.resize(n + 1);
    neg_occurs.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            std::cin >> clauses[i][j];
            int literal = clauses[i][j];
            if (literal > 0) {
                pos_occurs[literal].push_back(i);
            } else {
                neg_occurs[-literal].push_back(i);
            }
        }
    }
}

inline bool eval_literal(int literal, const std::vector<int>& assign) {
    if (literal > 0) return assign[literal];
    return !assign[-literal];
}

void compute_initial_state() {
    num_true_literals.assign(m, 0);
    for (int i = 0; i < m; ++i) {
        for (int literal : clauses[i]) {
            if (eval_literal(literal, assignment)) {
                num_true_literals[i]++;
            }
        }
    }

    unsatisfied_clauses_indices.clear();
    where_in_unsat.assign(m, -1);
    for (int i = 0; i < m; ++i) {
        if (num_true_literals[i] == 0) {
            where_in_unsat[i] = unsatisfied_clauses_indices.size();
            unsatisfied_clauses_indices.push_back(i);
        }
    }
}

int count_breaks(int var) {
    int breaks = 0;
    if (assignment[var]) {
        for (int clause_idx : pos_occurs[var]) {
            if (num_true_literals[clause_idx] == 1) {
                breaks++;
            }
        }
    } else {
        for (int clause_idx : neg_occurs[var]) {
            if (num_true_literals[clause_idx] == 1) {
                breaks++;
            }
        }
    }
    return breaks;
}

void add_to_unsat(int c_idx) {
    if (where_in_unsat[c_idx] == -1) {
        where_in_unsat[c_idx] = unsatisfied_clauses_indices.size();
        unsatisfied_clauses_indices.push_back(c_idx);
    }
}

void remove_from_unsat(int c_idx) {
    if (where_in_unsat[c_idx] != -1) {
        int pos = where_in_unsat[c_idx];
        int last_c_idx = unsatisfied_clauses_indices.back();
        
        unsatisfied_clauses_indices[pos] = last_c_idx;
        where_in_unsat[last_c_idx] = pos;
        
        unsatisfied_clauses_indices.pop_back();
        where_in_unsat[c_idx] = -1;
    }
}

void flip(int var) {
    bool old_val = assignment[var];
    assignment[var] = 1 - old_val;

    if (old_val) { // Was TRUE, now FALSE
        for (int c_idx : pos_occurs[var]) {
            num_true_literals[c_idx]--;
            if (num_true_literals[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
        for (int c_idx : neg_occurs[var]) {
            if (num_true_literals[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            num_true_literals[c_idx]++;
        }
    } else { // Was FALSE, now TRUE
        for (int c_idx : pos_occurs[var]) {
            if (num_true_literals[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            num_true_literals[c_idx]++;
        }
        for (int c_idx : neg_occurs[var]) {
            num_true_literals[c_idx]--;
            if (num_true_literals[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
    }
}

void solve() {
    read_input();
    
    assignment.resize(n + 1);
    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> bool_dist(0, 1);
    for (int i = 1; i <= n; ++i) {
        assignment[i] = bool_dist(rng);
    }
    
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            std::cout << assignment[i] << (i == n ? "" : " ");
        }
        std::cout << "\n";
        return;
    }

    compute_initial_state();
    
    min_unsatisfied_count = unsatisfied_clauses_indices.size();
    best_assignment = assignment;

    auto start_time = std::chrono::steady_clock::now();
    double time_limit = 1.95;

    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::duration<double>>(current_time - start_time).count() > time_limit) {
            break;
        }

        if (unsatisfied_clauses_indices.empty()) {
            min_unsatisfied_count = 0;
            best_assignment = assignment;
            break;
        }

        if (unsatisfied_clauses_indices.size() < min_unsatisfied_count) {
            min_unsatisfied_count = unsatisfied_clauses_indices.size();
            best_assignment = assignment;
        }

        std::uniform_int_distribution<int> clause_dist(0, unsatisfied_clauses_indices.size() - 1);
        int c_idx = unsatisfied_clauses_indices[clause_dist(rng)];

        int v_to_flip;
        std::uniform_real_distribution<double> p_dist(0.0, 1.0);
        if (p_dist(rng) < P_NOISE) {
            std::uniform_int_distribution<int> lit_dist(0, 2);
            v_to_flip = std::abs(clauses[c_idx][lit_dist(rng)]);
        } else {
            std::vector<int> vars_in_clause;
            for(int lit : clauses[c_idx]) {
                vars_in_clause.push_back(std::abs(lit));
            }
            std::sort(vars_in_clause.begin(), vars_in_clause.end());
            vars_in_clause.erase(std::unique(vars_in_clause.begin(), vars_in_clause.end()), vars_in_clause.end());
            
            int min_b = m + 1;
            std::vector<int> best_vars;
            
            for(int v : vars_in_clause) {
                int b = count_breaks(v);
                if (b < min_b) {
                    min_b = b;
                    best_vars.clear();
                    best_vars.push_back(v);
                } else if (b == min_b) {
                    best_vars.push_back(v);
                }
            }
            
            std::uniform_int_distribution<int> best_var_dist(0, best_vars.size() - 1);
            v_to_flip = best_vars[best_var_dist(rng)];
        }
        
        flip(v_to_flip);
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}