#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <tuple>
#include <numeric>
#include <algorithm>

// Globals for convenience, to be used within solve()
int n, m;
std::vector<std::tuple<int, int, int>> clauses;
std::vector<std::vector<int>> pos_clauses;
std::vector<std::vector<int>> neg_clauses;

void solve(std::vector<bool>& final_assignment) {
    if (m == 0) {
        final_assignment.assign(n + 1, false);
        return;
    }

    pos_clauses.assign(n + 1, std::vector<int>());
    neg_clauses.assign(n + 1, std::vector<int>());
    for (int i = 0; i < m; ++i) {
        auto [l1, l2, l3] = clauses[i];
        if (l1 > 0) pos_clauses[l1].push_back(i); else neg_clauses[-l1].push_back(i);
        if (l2 > 0) pos_clauses[l2].push_back(i); else neg_clauses[-l2].push_back(i);
        if (l3 > 0) pos_clauses[l3].push_back(i); else neg_clauses[-l3].push_back(i);
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> bool_dist(0, 1);

    std::vector<bool> current_assignment(n + 1);
    for (int i = 1; i <= n; ++i) {
        current_assignment[i] = bool_dist(rng);
    }
    
    std::vector<int> num_true_literals(m, 0);
    int current_satisfied_count = 0;
    
    auto is_true_local = [&](int literal, const std::vector<bool>& assign) {
        if (literal > 0) return assign[literal];
        return !assign[-literal];
    };

    for (int i = 0; i < m; ++i) {
        auto [l1, l2, l3] = clauses[i];
        if (is_true_local(l1, current_assignment)) num_true_literals[i]++;
        if (is_true_local(l2, current_assignment)) num_true_literals[i]++;
        if (is_true_local(l3, current_assignment)) num_true_literals[i]++;
        if (num_true_literals[i] > 0) {
            current_satisfied_count++;
        }
    }
    
    std::vector<bool> best_assignment = current_assignment;
    int best_satisfied_count = current_satisfied_count;

    if (best_satisfied_count == m) {
        final_assignment = best_assignment;
        return;
    }

    std::uniform_int_distribution<int> var_dist(1, n);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);
    
    double T = 1.0; 
    double alpha = 0.99999;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    int time_limit_ms = 1900; 

    for (int iter = 0; ; ++iter) {
        if (iter % 1024 == 0) {
            auto now = std::chrono::high_resolution_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time).count() > time_limit_ms) {
                break;
            }
        }
        
        int var_to_flip = var_dist(rng);
        
        int delta_satisfied = 0;
        bool original_value = current_assignment[var_to_flip];
        
        if (original_value) { // Flipping TRUE to FALSE
            for (int clause_idx : pos_clauses[var_to_flip]) {
                if (num_true_literals[clause_idx] == 1) {
                    delta_satisfied--;
                }
            }
            for (int clause_idx : neg_clauses[var_to_flip]) {
                if (num_true_literals[clause_idx] == 0) {
                    delta_satisfied++;
                }
            }
        } else { // Flipping FALSE to TRUE
            for (int clause_idx : pos_clauses[var_to_flip]) {
                if (num_true_literals[clause_idx] == 0) {
                    delta_satisfied++;
                }
            }
            for (int clause_idx : neg_clauses[var_to_flip]) {
                if (num_true_literals[clause_idx] == 1) {
                    delta_satisfied--;
                }
            }
        }
        
        if (delta_satisfied >= 0 || (T > 1e-9 && prob_dist(rng) < exp(delta_satisfied / T))) {
            current_assignment[var_to_flip] = !original_value;
            
            if (original_value) { // Was TRUE, now FALSE
                for (int clause_idx : pos_clauses[var_to_flip]) num_true_literals[clause_idx]--;
                for (int clause_idx : neg_clauses[var_to_flip]) num_true_literals[clause_idx]++;
            } else { // Was FALSE, now TRUE
                for (int clause_idx : pos_clauses[var_to_flip]) num_true_literals[clause_idx]++;
                for (int clause_idx : neg_clauses[var_to_flip]) num_true_literals[clause_idx]--;
            }
            
            current_satisfied_count += delta_satisfied;
            
            if (current_satisfied_count > best_satisfied_count) {
                best_satisfied_count = current_satisfied_count;
                best_assignment = current_assignment;
                if (best_satisfied_count == m) {
                    break; 
                }
            }
        }
        
        T *= alpha;
    }
    
    final_assignment = best_assignment;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    clauses.resize(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> std::get<0>(clauses[i]) >> std::get<1>(clauses[i]) >> std::get<2>(clauses[i]);
    }
    
    std::vector<bool> final_assignment;
    solve(final_assignment);
    
    for (int i = 1; i <= n; ++i) {
        std::cout << final_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}