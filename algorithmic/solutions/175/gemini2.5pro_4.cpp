#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>
#include <numeric>
#include <algorithm>

// Global variables
int n, m;

struct Clause {
    int l1, l2, l3;
};
std::vector<Clause> clauses;

std::vector<bool> assignment;
std::vector<bool> best_assignment;
int best_s;

std::vector<std::vector<int>> pos_clauses;
std::vector<std::vector<int>> neg_clauses;

std::vector<int> sat_count;
std::vector<int> unsatisfied_clauses;
std::vector<int> where_in_unsat;

std::mt19937 rng;

void read_input() {
    std::cin >> n >> m;
    clauses.resize(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> clauses[i].l1 >> clauses[i].l2 >> clauses[i].l3;
    }
}

void build_adj_lists() {
    pos_clauses.assign(n + 1, std::vector<int>());
    neg_clauses.assign(n + 1, std::vector<int>());
    for (int i = 0; i < m; ++i) {
        int v1 = std::abs(clauses[i].l1);
        int v2 = std::abs(clauses[i].l2);
        int v3 = std::abs(clauses[i].l3);

        if (clauses[i].l1 > 0) pos_clauses[v1].push_back(i); else neg_clauses[v1].push_back(i);
        if (clauses[i].l2 > 0) pos_clauses[v2].push_back(i); else neg_clauses[v2].push_back(i);
        if (clauses[i].l3 > 0) pos_clauses[v3].push_back(i); else neg_clauses[v3].push_back(i);
    }
}

void initial_random_assignment() {
    assignment.resize(n + 1);
    std::uniform_int_distribution<int> dist(0, 1);
    for (int i = 1; i <= n; ++i) {
        assignment[i] = dist(rng);
    }
}

void update_unsat_list(int clause_idx, int old_count, int new_count) {
    if (old_count == 0 && new_count > 0) { // becomes satisfied
        int pos = where_in_unsat[clause_idx];
        int last_clause_idx = unsatisfied_clauses.back();
        
        if (pos < unsatisfied_clauses.size() - 1) {
            unsatisfied_clauses[pos] = last_clause_idx;
            where_in_unsat[last_clause_idx] = pos;
        }
        
        unsatisfied_clauses.pop_back();
        where_in_unsat[clause_idx] = -1;
    } else if (old_count > 0 && new_count == 0) { // becomes unsatisfied
        where_in_unsat[clause_idx] = unsatisfied_clauses.size();
        unsatisfied_clauses.push_back(clause_idx);
    }
}

int calculate_gain(int var_to_flip) {
    int gain = 0;
    bool current_val = assignment[var_to_flip];

    for (int clause_idx : pos_clauses[var_to_flip]) {
        if (current_val) { // v is TRUE, becomes FALSE
            if (sat_count[clause_idx] == 1) gain--;
        } else { // v is FALSE, becomes TRUE
            if (sat_count[clause_idx] == 0) gain++;
        }
    }
    for (int clause_idx : neg_clauses[var_to_flip]) {
        if (!current_val) { // !v is TRUE, becomes FALSE
            if (sat_count[clause_idx] == 1) gain--;
        } else { // !v is FALSE, becomes TRUE
            if (sat_count[clause_idx] == 0) gain++;
        }
    }
    return gain;
}

void flip_variable(int var_to_flip) {
    bool old_val = assignment[var_to_flip];
    assignment[var_to_flip] = !old_val;

    for (int clause_idx : pos_clauses[var_to_flip]) {
        int old_sc = sat_count[clause_idx];
        if (old_val) sat_count[clause_idx]--; else sat_count[clause_idx]++;
        update_unsat_list(clause_idx, old_sc, sat_count[clause_idx]);
    }

    for (int clause_idx : neg_clauses[var_to_flip]) {
        int old_sc = sat_count[clause_idx];
        if (!old_val) sat_count[clause_idx]--; else sat_count[clause_idx]++;
        update_unsat_list(clause_idx, old_sc, sat_count[clause_idx]);
    }
}

void solve() {
    read_input();
    if (m == 0) {
        for (int i = 0; i < n; ++i) std::cout << "0" << (i == n - 1 ? "" : " ");
        std::cout << std::endl;
        return;
    }

    build_adj_lists();

    auto seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    rng.seed(seed);
    
    best_s = -1;

    int num_restarts = 5;
    for (int restart = 0; restart < num_restarts; ++restart) {
        initial_random_assignment();

        sat_count.assign(m, 0);
        unsatisfied_clauses.clear();
        where_in_unsat.assign(m, -1);
        for (int i = 0; i < m; ++i) {
            int v1 = std::abs(clauses[i].l1), v2 = std::abs(clauses[i].l2), v3 = std::abs(clauses[i].l3);
            bool val1 = (clauses[i].l1 > 0) ? assignment[v1] : !assignment[v1];
            bool val2 = (clauses[i].l2 > 0) ? assignment[v2] : !assignment[v2];
            bool val3 = (clauses[i].l3 > 0) ? assignment[v3] : !assignment[v3];
            sat_count[i] = val1 + val2 + val3;
            if (sat_count[i] == 0) {
                where_in_unsat[i] = unsatisfied_clauses.size();
                unsatisfied_clauses.push_back(i);
            }
        }
        
        int current_s = m - unsatisfied_clauses.size();
        if (current_s > best_s) {
            best_s = current_s;
            best_assignment = assignment;
        }

        int max_flips = 50000;
        for (int flip_iter = 0; flip_iter < max_flips; ++flip_iter) {
            if (unsatisfied_clauses.empty()) break;
            
            std::uniform_int_distribution<int> clause_dist(0, unsatisfied_clauses.size() - 1);
            int unsat_clause_idx = unsatisfied_clauses[clause_dist(rng)];

            std::uniform_real_distribution<double> prob_dist(0.0, 1.0);
            int var_to_flip = -1;
            
            if (prob_dist(rng) < 0.3) {
                 int vars_in_clause[3] = {std::abs(clauses[unsat_clause_idx].l1), 
                                         std::abs(clauses[unsat_clause_idx].l2),
                                         std::abs(clauses[unsat_clause_idx].l3)};
                 std::uniform_int_distribution<int> var_dist(0, 2);
                 var_to_flip = vars_in_clause[var_dist(rng)];
            } else {
                int v1 = std::abs(clauses[unsat_clause_idx].l1);
                int v2 = std::abs(clauses[unsat_clause_idx].l2);
                int v3 = std::abs(clauses[unsat_clause_idx].l3);
                int g1 = calculate_gain(v1), g2 = calculate_gain(v2), g3 = calculate_gain(v3);
                
                int max_g = std::max({g1, g2, g3});
                int candidates[3];
                int count = 0;
                if (g1 == max_g) candidates[count++] = v1;
                if (g2 == max_g) candidates[count++] = v2;
                if (g3 == max_g) candidates[count++] = v3;
                
                std::uniform_int_distribution<int> cand_dist(0, count - 1);
                var_to_flip = candidates[cand_dist(rng)];
            }

            flip_variable(var_to_flip);
            
            current_s = m - unsatisfied_clauses.size();
            if (current_s > best_s) {
                best_s = current_s;
                best_assignment = assignment;
            }
        }
        if (best_s == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}