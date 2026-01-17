#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>
#include <algorithm>

struct Clause {
    int l[3];
};

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

    std::vector<Clause> clauses(m);
    std::vector<std::vector<int>> where_var(n + 1);
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i].l[0] >> clauses[i].l[1] >> clauses[i].l[2];
        int vars[3] = {std::abs(clauses[i].l[0]), std::abs(clauses[i].l[1]), std::abs(clauses[i].l[2])};
        std::sort(vars, vars + 3);
        for(int j = 0; j < 3; ++j) {
            if (j == 0 || vars[j] != vars[j-1]) {
                where_var[vars[j]].push_back(i);
            }
        }
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    std::vector<int> best_assignment(n + 1);
    int min_unsat_count = m + 1;

    auto start_time = std::chrono::steady_clock::now();

    while (true) {
        auto current_time = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count() > 1900) {
            break;
        }

        std::vector<int> assignment(n + 1);
        std::uniform_int_distribution<int> bin_dist(0, 1);
        for (int i = 1; i <= n; ++i) {
            assignment[i] = bin_dist(rng);
        }

        std::vector<int> num_true_literals(m, 0);
        std::vector<int> unsat_clauses;
        std::vector<int> pos_in_unsat(m, -1);

        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < 3; ++j) {
                int literal = clauses[i].l[j];
                int var = std::abs(literal);
                bool is_neg = literal < 0;
                if ((assignment[var] == 1 && !is_neg) || (assignment[var] == 0 && is_neg)) {
                    num_true_literals[i]++;
                }
            }
            if (num_true_literals[i] == 0) {
                pos_in_unsat[i] = unsat_clauses.size();
                unsat_clauses.push_back(i);
            }
        }
        
        if (unsat_clauses.size() < min_unsat_count) {
            min_unsat_count = unsat_clauses.size();
            best_assignment = assignment;
            if (min_unsat_count == 0) break;
        }

        const int STEPS = 300000; 
        for (int step = 0; step < STEPS; ++step) {
            if (unsat_clauses.empty()) {
                break;
            }

            std::uniform_int_distribution<int> unsat_dist(0, unsat_clauses.size() - 1);
            int c_idx = unsat_clauses[unsat_dist(rng)];

            std::uniform_int_distribution<int> literal_dist(0, 2);
            int var_to_flip = std::abs(clauses[c_idx].l[literal_dist(rng)]);

            assignment[var_to_flip] = 1 - assignment[var_to_flip];

            for (int affected_c_idx : where_var[var_to_flip]) {
                int old_num_true = num_true_literals[affected_c_idx];
                
                int new_num_true = 0;
                for(int j=0; j<3; ++j) {
                    int literal = clauses[affected_c_idx].l[j];
                    int var = std::abs(literal);
                    bool is_neg = literal < 0;
                    if ((assignment[var] == 1 && !is_neg) || (assignment[var] == 0 && is_neg)) {
                        new_num_true++;
                    }
                }
                num_true_literals[affected_c_idx] = new_num_true;

                if (old_num_true > 0 && new_num_true == 0) {
                    pos_in_unsat[affected_c_idx] = unsat_clauses.size();
                    unsat_clauses.push_back(affected_c_idx);
                } else if (old_num_true == 0 && new_num_true > 0) {
                    int idx_to_remove = pos_in_unsat[affected_c_idx];
                    
                    int back_c_idx = unsat_clauses.back();
                    std::swap(unsat_clauses[idx_to_remove], unsat_clauses.back());
                    pos_in_unsat[back_c_idx] = idx_to_remove;
                    
                    unsat_clauses.pop_back();
                    pos_in_unsat[affected_c_idx] = -1;
                }
            }
            
            if (unsat_clauses.size() < min_unsat_count) {
                min_unsat_count = unsat_clauses.size();
                best_assignment = assignment;
                if (min_unsat_count == 0) break;
            }
        }
        if (min_unsat_count == 0) break;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}