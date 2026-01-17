#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <chrono>
#include <algorithm>

struct Clause {
    int l1, l2, l3;
};

int n, m;
std::vector<Clause> clauses;
std::vector<char> assignment;
std::vector<char> best_assignment;
int best_satisfied_count = -1;

std::vector<std::vector<int>> var_to_clauses_pos;
std::vector<std::vector<int>> var_to_clauses_neg;
std::vector<int> sat_counts;
std::vector<int> unsatisfied_clauses;
std::vector<int> pos_in_unsat;

std::mt19937 rng;

void initialize_random_assignment() {
    std::uniform_int_distribution<int> dist(0, 1);
    for (int i = 1; i <= n; ++i) {
        assignment[i] = dist(rng);
    }
}

bool is_true(int literal) {
    if (literal > 0) {
        return assignment[literal];
    } else {
        return !assignment[-literal];
    }
}

void calculate_initial_sat_counts() {
    unsatisfied_clauses.clear();
    std::fill(pos_in_unsat.begin(), pos_in_unsat.end(), -1);
    for (int i = 0; i < m; ++i) {
        sat_counts[i] = is_true(clauses[i].l1) + is_true(clauses[i].l2) + is_true(clauses[i].l3);
        if (sat_counts[i] == 0) {
            pos_in_unsat[i] = unsatisfied_clauses.size();
            unsatisfied_clauses.push_back(i);
        }
    }
}

void remove_from_unsat(int clause_idx) {
    if (pos_in_unsat[clause_idx] == -1) return;
    int idx_in_vec = pos_in_unsat[clause_idx];
    int last_clause_idx = unsatisfied_clauses.back();

    unsatisfied_clauses[idx_in_vec] = last_clause_idx;
    pos_in_unsat[last_clause_idx] = idx_in_vec;

    unsatisfied_clauses.pop_back();
    pos_in_unsat[clause_idx] = -1;
}

void add_to_unsat(int clause_idx) {
    if (pos_in_unsat[clause_idx] != -1) return;
    pos_in_unsat[clause_idx] = unsatisfied_clauses.size();
    unsatisfied_clauses.push_back(clause_idx);
}

void flip_variable(int var_idx) {
    bool old_val = assignment[var_idx];
    assignment[var_idx] = !old_val;

    if (!old_val) { // Flipped 0 -> 1
        for (int c_idx : var_to_clauses_pos[var_idx]) {
            if (sat_counts[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            sat_counts[c_idx]++;
        }
        for (int c_idx : var_to_clauses_neg[var_idx]) {
            sat_counts[c_idx]--;
            if (sat_counts[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
    } else { // Flipped 1 -> 0
        for (int c_idx : var_to_clauses_pos[var_idx]) {
            sat_counts[c_idx]--;
            if (sat_counts[c_idx] == 0) {
                add_to_unsat(c_idx);
            }
        }
        for (int c_idx : var_to_clauses_neg[var_idx]) {
            if (sat_counts[c_idx] == 0) {
                remove_from_unsat(c_idx);
            }
            sat_counts[c_idx]++;
        }
    }
}

void solve() {
    initialize_random_assignment();
    calculate_initial_sat_counts();
    best_assignment = assignment;
    best_satisfied_count = m - unsatisfied_clauses.size();

    if (best_satisfied_count == m) return;

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_seconds = 1.9;

    double avg_degree = 3.0 * m / n;
    int max_flips = 30000000 / (avg_degree + 1);
    if (max_flips < 100) max_flips = 100;

    bool found_perfect = false;
    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_seconds) break;
        
        initialize_random_assignment();
        calculate_initial_sat_counts();

        if (m - (int)unsatisfied_clauses.size() > best_satisfied_count) {
            best_satisfied_count = m - unsatisfied_clauses.size();
            best_assignment = assignment;
            if (best_satisfied_count == m) break;
        }

        for (int flip = 0; flip < max_flips; ++flip) {
            if (unsatisfied_clauses.empty()) {
                best_satisfied_count = m;
                best_assignment = assignment;
                found_perfect = true;
                break;
            }

            std::uniform_int_distribution<size_t> unsat_dist(0, unsatisfied_clauses.size() - 1);
            int c_idx = unsatisfied_clauses[unsat_dist(rng)];

            std::uniform_int_distribution<int> var_dist(0, 2);
            int literal_choice = var_dist(rng);
            int literal_to_flip;
            if (literal_choice == 0) literal_to_flip = clauses[c_idx].l1;
            else if (literal_choice == 1) literal_to_flip = clauses[c_idx].l2;
            else literal_to_flip = clauses[c_idx].l3;

            int var_to_flip = std::abs(literal_to_flip);
            flip_variable(var_to_flip);
            
            if (m - (int)unsatisfied_clauses.size() > best_satisfied_count) {
                best_satisfied_count = m - unsatisfied_clauses.size();
                best_assignment = assignment;
            }
        }
        if (found_perfect) break;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    rng.seed(std::chrono::steady_clock::now().time_since_epoch().count());

    std::cin >> n >> m;
    
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            std::cout << "0" << (i == n - 1 ? "" : " ");
        }
        std::cout << std::endl;
        return 0;
    }

    clauses.resize(m);
    var_to_clauses_pos.resize(n + 1);
    var_to_clauses_neg.resize(n + 1);
    assignment.resize(n + 1);
    best_assignment.resize(n + 1);
    sat_counts.resize(m);
    pos_in_unsat.resize(m);

    for (int i = 0; i < m; ++i) {
        int u, v, w;
        std::cin >> u >> v >> w;
        clauses[i] = {u, v, w};
        if (u > 0) var_to_clauses_pos[u].push_back(i); else var_to_clauses_neg[-u].push_back(i);
        if (v > 0) var_to_clauses_pos[v].push_back(i); else var_to_clauses_neg[-v].push_back(i);
        if (w > 0) var_to_clauses_pos[w].push_back(i); else var_to_clauses_neg[-w].push_back(i);
    }

    for (int i = 1; i <= n; ++i) {
        std::sort(var_to_clauses_pos[i].begin(), var_to_clauses_pos[i].end());
        var_to_clauses_pos[i].erase(std::unique(var_to_clauses_pos[i].begin(), var_to_clauses_pos[i].end()), var_to_clauses_pos[i].end());
        std::sort(var_to_clauses_neg[i].begin(), var_to_clauses_neg[i].end());
        var_to_clauses_neg[i].erase(std::unique(var_to_clauses_neg[i].begin(), var_to_clauses_neg[i].end()), var_to_clauses_neg[i].end());
    }

    solve();

    for (int i = 1; i <= n; ++i) {
        std::cout << (int)best_assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}