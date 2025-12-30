#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <chrono>
#include <algorithm>
#include <array>

// Converts a literal to a variable index (1-based) and its sign (true for positive)
std::pair<int, bool> literal_to_var(int literal) {
    if (literal > 0) return {literal, true};
    return {-literal, false};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return 0;
    }

    std::vector<std::array<int, 3>> clauses(m);
    std::vector<std::vector<int>> pos_clauses(n + 1);
    std::vector<std::vector<int>> neg_clauses(n + 1);

    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
        for (int lit : clauses[i]) {
            auto [var, is_pos] = literal_to_var(lit);
            if (is_pos) {
                pos_clauses[var].push_back(i);
            } else {
                neg_clauses[var].push_back(i);
            }
        }
    }
    
    // Remove duplicate clause entries for variables which can occur if a variable
    // appears multiple times in the same clause (e.g., a v a v b)
    for (int i = 1; i <= n; ++i) {
        std::sort(pos_clauses[i].begin(), pos_clauses[i].end());
        pos_clauses[i].erase(std::unique(pos_clauses[i].begin(), pos_clauses[i].end()), pos_clauses[i].end());
        std::sort(neg_clauses[i].begin(), neg_clauses[i].end());
        neg_clauses[i].erase(std::unique(neg_clauses[i].begin(), neg_clauses[i].end()), neg_clauses[i].end());
    }

    std::vector<bool> best_assignment(n + 1);
    int best_satisfied_count = -1;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    auto start_time = std::chrono::steady_clock::now();
    double time_limit_sec = 1.95; 

    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_sec) {
            break;
        }
        
        std::vector<bool> current_assignment(n + 1);
        for (int i = 1; i <= n; ++i) {
            current_assignment[i] = std::uniform_int_distribution<int>(0, 1)(rng);
        }

        std::vector<int> num_true_literals(m, 0);
        int current_satisfied_count = 0;
        for (int i = 0; i < m; ++i) {
            for (int lit : clauses[i]) {
                auto [var, is_pos] = literal_to_var(lit);
                if ((is_pos && current_assignment[var]) || (!is_pos && !current_assignment[var])) {
                    num_true_literals[i]++;
                }
            }
            if (num_true_literals[i] > 0) {
                current_satisfied_count++;
            }
        }

        std::vector<int> vars_to_check(n);
        std::iota(vars_to_check.begin(), vars_to_check.end(), 1);

        for (int pass = 0; pass < 60; ++pass) {
            bool changed_in_pass = false;
            std::shuffle(vars_to_check.begin(), vars_to_check.end(), rng);

            for (int var : vars_to_check) {
                int gain = 0;
                if (!current_assignment[var]) { // currently FALSE, try flipping to TRUE
                    for (int c_idx : pos_clauses[var]) {
                        if (num_true_literals[c_idx] == 0) gain++;
                    }
                    for (int c_idx : neg_clauses[var]) {
                        if (num_true_literals[c_idx] == 1) gain--;
                    }
                } else { // currently TRUE, try flipping to FALSE
                    for (int c_idx : neg_clauses[var]) {
                        if (num_true_literals[c_idx] == 0) gain++;
                    }
                    for (int c_idx : pos_clauses[var]) {
                        if (num_true_literals[c_idx] == 1) gain--;
                    }
                }

                if (gain > 0) {
                    changed_in_pass = true;
                    current_satisfied_count += gain;
                    
                    if (!current_assignment[var]) { // flipping FALSE -> TRUE
                        for (int c_idx : pos_clauses[var]) num_true_literals[c_idx]++;
                        for (int c_idx : neg_clauses[var]) num_true_literals[c_idx]--;
                    } else { // flipping TRUE -> FALSE
                        for (int c_idx : neg_clauses[var]) num_true_literals[c_idx]++;
                        for (int c_idx : pos_clauses[var]) num_true_literals[c_idx]--;
                    }
                    current_assignment[var] = !current_assignment[var];
                }
            }
            if (!changed_in_pass) {
                break;
            }
        }

        if (current_satisfied_count > best_satisfied_count) {
            best_satisfied_count = current_satisfied_count;
            best_assignment = current_assignment;
            if (best_satisfied_count == m) break; 
        }
    }

    if (best_satisfied_count == -1) {
        for (int i = 1; i <= n; ++i) best_assignment[i] = 0;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}