#include <iostream>
#include <vector>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;
using namespace std::chrono;

struct Clause {
    int l1, l2, l3;
};

int n, m;
vector<Clause> clauses;
vector<int> assignment;
vector<int> best_assignment;
int max_satisfied = -1;

// Helper to evaluate a literal
bool eval_lit(int lit, const vector<int>& assign) {
    if (lit > 0) return assign[lit];
    else return !assign[-lit];
}

// Evaluate total satisfied clauses
int evaluate(const vector<int>& assign) {
    int sat = 0;
    for (const auto& c : clauses) {
        if (eval_lit(c.l1, assign) || eval_lit(c.l2, assign) || eval_lit(c.l3, assign)) {
            sat++;
        }
    }
    return sat;
}

// Get indices of all unsatisfied clauses
vector<int> get_unsatisfied_indices(const vector<int>& assign) {
    vector<int> unsat;
    unsat.reserve(m);
    for (int i = 0; i < m; ++i) {
        const auto& c = clauses[i];
        if (!(eval_lit(c.l1, assign) || eval_lit(c.l2, assign) || eval_lit(c.l3, assign))) {
            unsat.push_back(i);
        }
    }
    return unsat;
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    clauses.resize(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].l1 >> clauses[i].l2 >> clauses[i].l3;
    }

    assignment.resize(n + 1);
    best_assignment.resize(n + 1, 0);

    if (m == 0) {
        for (int i = 1; i <= n; ++i) cout << "0" << (i == n ? "" : " ");
        cout << "\n";
        return 0;
    }

    // Initialize RNG
    mt19937 rng(1337);
    uniform_int_distribution<int> dist_bool(0, 1);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    auto start_time = high_resolution_clock::now();
    double time_limit = 0.85; // Set slightly below 1s to be safe

    // Initial random assignment
    for (int i = 1; i <= n; ++i) assignment[i] = dist_bool(rng);
    max_satisfied = evaluate(assignment);
    best_assignment = assignment;

    while (true) {
        // Check time limit
        duration<double> diff = high_resolution_clock::now() - start_time;
        if (diff.count() > time_limit) break;
        if (max_satisfied == m) break;

        // Restart with a new random assignment
        for (int i = 1; i <= n; ++i) assignment[i] = dist_bool(rng);
        int current_score = evaluate(assignment);
        if (current_score > max_satisfied) {
            max_satisfied = current_score;
            best_assignment = assignment;
        }

        // Run Local Search (WalkSAT) for a limited number of steps
        for (int step = 0; step < 2500; ++step) {
            vector<int> unsat = get_unsatisfied_indices(assignment);
            if (unsat.empty()) {
                max_satisfied = m;
                best_assignment = assignment;
                break;
            }

            // Pick a random unsatisfied clause
            uniform_int_distribution<int> dist_idx(0, unsat.size() - 1);
            int c_idx = unsat[dist_idx(rng)];
            const Clause& c = clauses[c_idx];
            
            int vars[3] = {abs(c.l1), abs(c.l2), abs(c.l3)};
            int best_v = vars[0];

            // WalkSAT strategy:
            // With probability p, pick a random variable from the clause to flip (Noise)
            // With probability 1-p, pick the variable that maximizes the total score (Greedy)
            if (dist_prob(rng) < 0.45) { 
                uniform_int_distribution<int> dist_3(0, 2);
                best_v = vars[dist_3(rng)];
            } else {
                int best_local_sat = -1;
                vector<int> candidates;
                for (int v : vars) {
                    assignment[v] = 1 - assignment[v]; // Try flip
                    int s = evaluate(assignment);
                    assignment[v] = 1 - assignment[v]; // Revert

                    if (s > best_local_sat) {
                        best_local_sat = s;
                        candidates.clear();
                        candidates.push_back(v);
                    } else if (s == best_local_sat) {
                        candidates.push_back(v);
                    }
                }
                if (!candidates.empty()) {
                    uniform_int_distribution<int> dist_cand(0, candidates.size() - 1);
                    best_v = candidates[dist_cand(rng)];
                }
            }

            // Apply the flip
            assignment[best_v] = 1 - assignment[best_v];
            int s = evaluate(assignment);
            
            if (s > max_satisfied) {
                max_satisfied = s;
                best_assignment = assignment;
                if (max_satisfied == m) break;
            }
        }
    }

    // Output the best solution found
    for (int i = 1; i <= n; ++i) {
        cout << best_assignment[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}