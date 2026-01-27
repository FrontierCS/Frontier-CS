#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <tuple>
#include <chrono>

// For random numbers, seeded once
std::mt19937 rng;

struct Clause {
    int l1, l2, l3;
};

int n, m;
std::vector<Clause> clauses;
std::vector<std::vector<int>> clauses_with_literal;
std::vector<bool> best_assignment;
int max_satisfied_clauses = -1;

// Map literal to index 0..2n-1
// lit > 0 (xi): maps to lit-1
// lit < 0 (-xi): maps to n + (-lit) - 1
int literal_to_idx(int lit) {
    if (lit > 0) return lit - 1;
    return n - lit - 1;
}

void run_walksat() {
    std::vector<bool> current_assignment(n + 1);
    for (int i = 1; i <= n; ++i) {
        current_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
    }

    if (m == 0) {
        if (max_satisfied_clauses < 0) {
            max_satisfied_clauses = 0;
            best_assignment = current_assignment;
        }
        return;
    }
    
    std::vector<int> num_true_literals(m);
    std::vector<int> unsatisfied_indices;
    std::vector<int> pos_in_unsatisfied(m, -1);
    int current_satisfied = 0;

    for (int i = 0; i < m; ++i) {
        auto eval_lit = [&](int lit){
            if (lit > 0) return current_assignment[lit];
            return !current_assignment[-lit];
        };
        num_true_literals[i] = eval_lit(clauses[i].l1) + eval_lit(clauses[i].l2) + eval_lit(clauses[i].l3);

        if (num_true_literals[i] > 0) {
            current_satisfied++;
        } else {
            pos_in_unsatisfied[i] = unsatisfied_indices.size();
            unsatisfied_indices.push_back(i);
        }
    }

    if (current_satisfied > max_satisfied_clauses) {
        max_satisfied_clauses = current_satisfied;
        best_assignment = current_assignment;
    }
    if (max_satisfied_clauses == m) return;

    const int MAX_ITERATIONS = 200000;
    const int P_RANDOM_WALK = 30;

    for (int iter = 0; iter < MAX_ITERATIONS; ++iter) {
        if (unsatisfied_indices.empty()) {
            max_satisfied_clauses = m;
            best_assignment = current_assignment;
            return;
        }

        int c_idx = unsatisfied_indices[std::uniform_int_distribution<int>(0, unsatisfied_indices.size() - 1)(rng)];
        
        int vars_in_clause[3] = {std::abs(clauses[c_idx].l1), std::abs(clauses[c_idx].l2), std::abs(clauses[c_idx].l3)};
        
        int var_to_flip;

        if (std::uniform_int_distribution<int>(0, 99)(rng) < P_RANDOM_WALK) {
            var_to_flip = vars_in_clause[std::uniform_int_distribution<int>(0, 2)(rng)];
        } else {
            std::sort(std::begin(vars_in_clause), std::end(vars_in_clause));
            int unique_vars_count = std::unique(std::begin(vars_in_clause), std::end(vars_in_clause)) - std::begin(vars_in_clause);

            int min_break_count = m + 1;
            std::vector<int> best_vars_to_flip;

            for (int i = 0; i < unique_vars_count; ++i) {
                int v = vars_in_clause[i];
                int break_count = 0;
                int literal_that_becomes_false = current_assignment[v] ? v : -v;
                for (int affected_c_idx : clauses_with_literal[literal_to_idx(literal_that_becomes_false)]) {
                    if (num_true_literals[affected_c_idx] == 1) {
                        break_count++;
                    }
                }
                if (break_count < min_break_count) {
                    min_break_count = break_count;
                    best_vars_to_flip.clear();
                    best_vars_to_flip.push_back(v);
                } else if (break_count == min_break_count) {
                    best_vars_to_flip.push_back(v);
                }
            }
            var_to_flip = best_vars_to_flip[std::uniform_int_distribution<int>(0, best_vars_to_flip.size() - 1)(rng)];
        }
        
        bool old_val = current_assignment[var_to_flip];
        current_assignment[var_to_flip] = !old_val;

        int literal_that_becomes_false = old_val ? var_to_flip : -var_to_flip;
        int literal_that_becomes_true = !old_val ? var_to_flip : -var_to_flip;

        for (int affected_c_idx : clauses_with_literal[literal_to_idx(literal_that_becomes_false)]) {
            if (num_true_literals[affected_c_idx] == 1) {
                current_satisfied--;
                pos_in_unsatisfied[affected_c_idx] = unsatisfied_indices.size();
                unsatisfied_indices.push_back(affected_c_idx);
            }
            num_true_literals[affected_c_idx]--;
        }
        
        for (int affected_c_idx : clauses_with_literal[literal_to_idx(literal_that_becomes_true)]) {
            if (num_true_literals[affected_c_idx] == 0) {
                current_satisfied++;
                int pos = pos_in_unsatisfied[affected_c_idx];
                int back_c_idx = unsatisfied_indices.back();
                
                unsatisfied_indices[pos] = back_c_idx;
                pos_in_unsatisfied[back_c_idx] = pos;
                unsatisfied_indices.pop_back();
                pos_in_unsatisfied[affected_c_idx] = -1;
            }
            num_true_literals[affected_c_idx]++;
        }
        
        if (current_satisfied > max_satisfied_clauses) {
            max_satisfied_clauses = current_satisfied;
            best_assignment = current_assignment;
            if (max_satisfied_clauses == m) return;
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    
    std::cin >> n >> m;
    
    clauses.resize(m);
    clauses_with_literal.resize(2 * n);
    
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i].l1 >> clauses[i].l2 >> clauses[i].l3;
        clauses_with_literal[literal_to_idx(clauses[i].l1)].push_back(i);
        clauses_with_literal[literal_to_idx(clauses[i].l2)].push_back(i);
        clauses_with_literal[literal_to_idx(clauses[i].l3)].push_back(i);
    }
    
    best_assignment.resize(n + 1, 0);

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit = 1.9;

    do {
        run_walksat();
        if (max_satisfied_clauses == m) {
            break;
        }
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit) {
            break;
        }
    } while (true);
    
    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}