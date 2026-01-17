#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <utility>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // clauses: for each clause, list of (var, is_positive)
    vector<vector<pair<int, bool>>> clauses(m);
    // for each variable, list of (clause_idx, is_positive)
    vector<vector<pair<int, bool>>> var_clauses(n);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        // helper lambda to process a literal
        auto add_literal = [&](int lit) {
            bool pos = (lit > 0);
            int var = (pos ? lit : -lit) - 1; // 0-indexed
            clauses[i].emplace_back(var, pos);
            var_clauses[var].emplace_back(i, pos);
        };
        add_literal(a);
        add_literal(b);
        add_literal(c);
    }

    // If no clauses, any assignment works.
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << " \n"[i == n-1];
        }
        return 0;
    }

    // Random number generation
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<int> rand_bit(0, 1);
    uniform_real_distribution<double> rand_prob(0.0, 1.0);

    // Initial random assignment
    vector<int> A(n);
    for (int i = 0; i < n; ++i) {
        A[i] = rand_bit(gen);
    }

    // true_literal_count for each clause
    vector<int> true_lit_count(m, 0);
    for (int i = 0; i < m; ++i) {
        for (auto& lit : clauses[i]) {
            int v = lit.first;
            bool pos = lit.second;
            if ((pos && A[v] == 1) || (!pos && A[v] == 0)) {
                true_lit_count[i]++;
            }
        }
    }

    // Current satisfied count
    int total_sat = 0;
    for (int i = 0; i < m; ++i) {
        if (true_lit_count[i] > 0) total_sat++;
    }

    // Best found so far
    vector<int> best_A = A;
    int best_sat = total_sat;

    const int MAX_ITER = 200000;
    const double NOISE_PROB = 0.3;

    for (int iter = 0; iter < MAX_ITER; ++iter) {
        if (total_sat == m) break; // all satisfied

        // Pick a random unsatisfied clause
        int c;
        do {
            c = uniform_int_distribution<int>(0, m-1)(gen);
        } while (true_lit_count[c] > 0);

        // Compute gain for each variable in this clause
        vector<pair<int, int>> gains; // (var, gain)
        for (auto& lit : clauses[c]) {
            int v = lit.first;
            int gain = 0;
            for (auto& occ : var_clauses[v]) {
                int cl = occ.first;
                bool pos = occ.second;
                int old_count = true_lit_count[cl];
                bool old_sat = (old_count > 0);
                bool cur_lit_true = (A[v] == pos);
                int delta = cur_lit_true ? -1 : 1;
                int new_count = old_count + delta;
                bool new_sat = (new_count > 0);
                gain += (new_sat - old_sat); // -1, 0, or 1
            }
            gains.emplace_back(v, gain);
        }

        // Choose variable to flip
        int v_flip;
        if (rand_prob(gen) < NOISE_PROB) {
            // random pick from clause
            int idx = uniform_int_distribution<int>(0, gains.size()-1)(gen);
            v_flip = gains[idx].first;
        } else {
            // pick variable with highest gain
            int max_gain = gains[0].second;
            for (auto& g : gains) {
                if (g.second > max_gain) max_gain = g.second;
            }
            vector<int> candidates;
            for (auto& g : gains) {
                if (g.second == max_gain) candidates.push_back(g.first);
            }
            int idx = uniform_int_distribution<int>(0, candidates.size()-1)(gen);
            v_flip = candidates[idx];
        }

        // Flip variable v_flip
        int old_val = A[v_flip];
        int new_val = 1 - old_val;
        // Update true_lit_count and total_sat for affected clauses
        for (auto& occ : var_clauses[v_flip]) {
            int cl = occ.first;
            bool pos = occ.second;
            bool cur_lit_true_before = (old_val == pos);
            int delta = cur_lit_true_before ? -1 : 1;
            int old_count = true_lit_count[cl];
            int new_count = old_count + delta;
            true_lit_count[cl] = new_count;
            bool old_sat = (old_count > 0);
            bool new_sat = (new_count > 0);
            if (old_sat != new_sat) {
                if (new_sat) total_sat++;
                else total_sat--;
            }
        }
        A[v_flip] = new_val;

        // Update best assignment
        if (total_sat > best_sat) {
            best_sat = total_sat;
            best_A = A;
        }
    }

    // Output best assignment
    for (int i = 0; i < n; ++i) {
        cout << best_A[i] << " \n"[i == n-1];
    }

    return 0;
}