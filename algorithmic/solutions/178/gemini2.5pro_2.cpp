#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>

// Global RNG
std::mt19937 rng;

// Helper to check if a literal is true given an assignment
bool is_literal_true(int literal, const std::vector<int>& assignment) {
    if (literal > 0) {
        return assignment[literal - 1] == 1;
    } else {
        return assignment[-literal - 1] == 0;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Seed RNG with a time-based value
    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());

    int n, m;
    std::cin >> n >> m;

    // Handle the m=0 case separately for simplicity
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << (i > 0 ? " " : "") << 0;
        }
        std::cout << std::endl;
        return 0;
    }

    std::vector<std::vector<int>> clauses(m, std::vector<int>(3));
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }

    // Pre-calculate which clauses each variable appears in
    std::vector<std::vector<int>> clauses_with_var(n);
    for (int i = 0; i < m; ++i) {
        std::vector<bool> seen(n, false);
        for (int literal : clauses[i]) {
            int var_idx = std::abs(literal) - 1;
            if (!seen[var_idx]) {
                clauses_with_var[var_idx].push_back(i);
                seen[var_idx] = true;
            }
        }
    }

    std::vector<int> best_assignment(n);
    int max_satisfied = -1;

    auto start_time = std::chrono::high_resolution_clock::now();

    // Loop with random restarts until time limit is approached
    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() < 1900) {
        
        // Start with a random assignment
        std::vector<int> current_assignment(n);
        std::uniform_int_distribution<int> dist(0, 1);
        for (int i = 0; i < n; ++i) {
            current_assignment[i] = dist(rng);
        }

        // Count true literals for each clause
        std::vector<int> true_literals_count(m, 0);
        for (int i = 0; i < m; ++i) {
            for (int literal : clauses[i]) {
                if (is_literal_true(literal, current_assignment)) {
                    true_literals_count[i]++;
                }
            }
        }

        // Steepest-ascent hill climbing
        while (true) {
            int best_var_to_flip = -1;
            int max_gain = 0;

            // Find the variable flip that yields the maximum gain
            for (int i = 0; i < n; ++i) {
                int gain = 0;
                for (int clause_idx : clauses_with_var[i]) {
                    bool old_sat = true_literals_count[clause_idx] > 0;
                    
                    int new_true_count = true_literals_count[clause_idx];
                    for (int literal : clauses[clause_idx]) {
                        if (std::abs(literal) == i + 1) {
                            if (is_literal_true(literal, current_assignment)) {
                                new_true_count--;
                            } else {
                                new_true_count++;
                            }
                        }
                    }
                    
                    bool new_sat = new_true_count > 0;

                    if (new_sat && !old_sat) {
                        gain++;
                    } else if (!new_sat && old_sat) {
                        gain--;
                    }
                }

                if (gain > max_gain) {
                    max_gain = gain;
                    best_var_to_flip = i;
                }
            }

            if (best_var_to_flip != -1) {
                // Apply the best flip
                int i = best_var_to_flip;
                // Update true literals counts for affected clauses
                for (int clause_idx : clauses_with_var[i]) {
                    for (int literal : clauses[clause_idx]) {
                        if (std::abs(literal) == i + 1) {
                            if (is_literal_true(literal, current_assignment)) {
                                true_literals_count[clause_idx]--;
                            } else {
                                true_literals_count[clause_idx]++;
                            }
                        }
                    }
                }
                current_assignment[i] = 1 - current_assignment[i];
            } else {
                // Local optimum reached
                break;
            }
        }

        // After hill climbing, check if this solution is the best one so far
        int current_satisfied = 0;
        for (int count : true_literals_count) {
            if (count > 0) {
                current_satisfied++;
            }
        }

        if (current_satisfied > max_satisfied) {
            max_satisfied = current_satisfied;
            best_assignment = current_assignment;
            // If all clauses are satisfied, we can stop early
            if (max_satisfied == m) {
                break;
            }
        }
    }

    if (max_satisfied == -1) { // Fallback for extremely short time limits
        std::uniform_int_distribution<int> dist(0, 1);
        for(int i = 0; i < n; ++i) {
            best_assignment[i] = dist(rng);
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << best_assignment[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}