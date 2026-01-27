#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>

// --- Random number generation ---
std::mt19937 gen;

// --- Problem data ---
int n, m;
std::vector<std::pair<int, int>> clauses;
std::vector<std::vector<int>> var_to_clauses;

// --- State representation ---
std::vector<int> assignment;
std::vector<int> unsatisfied_clauses_indices;
std::vector<int> where_in_unsatisfied;
int num_satisfied_clauses;

// --- Best solution found ---
std::vector<int> best_assignment;
int max_satisfied_clauses;

// --- Helper functions ---

inline bool eval_lit_in_current_assignment(int lit) {
    if (lit > 0) {
        return assignment[lit] == 1;
    }
    return assignment[-lit] == 0;
}

bool is_clause_satisfied(int clause_idx) {
    return eval_lit_in_current_assignment(clauses[clause_idx].first) || eval_lit_in_current_assignment(clauses[clause_idx].second);
}

int calculate_gain(int var_to_flip) {
    int gain = 0;
    for (int clause_idx : var_to_clauses[var_to_flip]) {
        bool original_sat = is_clause_satisfied(clause_idx);
        
        assignment[var_to_flip] = 1 - assignment[var_to_flip];
        bool flipped_sat = is_clause_satisfied(clause_idx);
        assignment[var_to_flip] = 1 - assignment[var_to_flip];

        if (!original_sat && flipped_sat) gain++;
        if (original_sat && !flipped_sat) gain--;
    }
    return gain;
}


void flip_variable(int var_to_flip) {
    for (int clause_idx : var_to_clauses[var_to_flip]) {
        auto [a, b] = clauses[clause_idx];
        int other_lit = (abs(a) == var_to_flip) ? b : a;

        if (eval_lit_in_current_assignment(other_lit)) {
            continue; 
        }
        
        bool was_satisfied = is_clause_satisfied(clause_idx);

        if (was_satisfied) {
            num_satisfied_clauses--;
            where_in_unsatisfied[clause_idx] = unsatisfied_clauses_indices.size();
            unsatisfied_clauses_indices.push_back(clause_idx);
        } else {
            num_satisfied_clauses++;
            int pos = where_in_unsatisfied[clause_idx];
            if (pos != -1) {
                int back_idx = unsatisfied_clauses_indices.back();
                if (pos < unsatisfied_clauses_indices.size() - 1) {
                    unsatisfied_clauses_indices[pos] = back_idx;
                    where_in_unsatisfied[back_idx] = pos;
                }
                unsatisfied_clauses_indices.pop_back();
                where_in_unsatisfied[clause_idx] = -1;
            }
        }
    }
    assignment[var_to_flip] = 1 - assignment[var_to_flip];
}

void solve() {
    std::cin >> n >> m;
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return;
    }

    clauses.resize(m);
    var_to_clauses.assign(n + 1, std::vector<int>());
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        clauses[i] = {u, v};
        var_to_clauses[abs(u)].push_back(i);
        if (abs(u) != abs(v)) {
            var_to_clauses[abs(v)].push_back(i);
        }
    }

    assignment.resize(n + 1);
    best_assignment.resize(n + 1);
    where_in_unsatisfied.resize(m, -1);
    max_satisfied_clauses = -1;

    auto start_time = std::chrono::steady_clock::now();
    long long time_limit_ms = 1900; 
    
    std::uniform_int_distribution<> coin(0, 1);
    std::uniform_int_distribution<> prob_dist(0, 99);
    const int P_RANDOM_WALK = 30;
    bool first_run = true;

    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() < time_limit_ms) {
        // 1. Random initial assignment
        for (int i = 1; i <= n; ++i) {
            assignment[i] = coin(gen);
        }

        // 2. Initial evaluation
        num_satisfied_clauses = 0;
        unsatisfied_clauses_indices.clear();
        for (int i = 0; i < m; ++i) {
            if (is_clause_satisfied(i)) {
                num_satisfied_clauses++;
                where_in_unsatisfied[i] = -1;
            } else {
                where_in_unsatisfied[i] = unsatisfied_clauses_indices.size();
                unsatisfied_clauses_indices.push_back(i);
            }
        }
        
        if (first_run || num_satisfied_clauses > max_satisfied_clauses) {
            max_satisfied_clauses = num_satisfied_clauses;
            best_assignment = assignment;
            first_run = false;
        }

        for (int flip_iter = 0; flip_iter < 300000 && !unsatisfied_clauses_indices.empty(); ++flip_iter) {
            if (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() >= time_limit_ms) break;

            std::uniform_int_distribution<int> unsat_dist(0, unsatisfied_clauses_indices.size() - 1);
            int clause_idx = unsatisfied_clauses_indices[unsat_dist(gen)];
            
            auto [a, b] = clauses[clause_idx];
            int var_a = abs(a);
            int var_b = abs(b);

            int var_to_flip;
            if (var_a != var_b && prob_dist(gen) < P_RANDOM_WALK) {
                var_to_flip = coin(gen) ? var_a : var_b;
            } else {
                int gain_a = calculate_gain(var_a);
                if (var_a == var_b) {
                    var_to_flip = var_a;
                } else {
                    int gain_b = calculate_gain(var_b);
                    if (gain_a > gain_b) {
                        var_to_flip = var_a;
                    } else if (gain_b > gain_a) {
                        var_to_flip = var_b;
                    } else {
                        var_to_flip = coin(gen) ? var_a : var_b;
                    }
                }
            }
            
            flip_variable(var_to_flip);

            if (num_satisfied_clauses > max_satisfied_clauses) {
                max_satisfied_clauses = num_satisfied_clauses;
                best_assignment = assignment;
                if (max_satisfied_clauses == m) break;
            }
        }
        if (max_satisfied_clauses == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::random_device rd;
    gen.seed(rd());

    solve();

    return 0;
}