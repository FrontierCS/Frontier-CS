#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <random>
#include <chrono>
#include <climits>

using namespace std;

// Constants matching constraints
const int MAXN = 405;

struct SetInfo {
    int id; // Original 1-based ID
    int cost;
    bitset<MAXN> mask; // bit i corresponds to element i+1
};

int n, m;
vector<SetInfo> sets;

// Global best tracking
long long best_total_cost = -1;
vector<int> best_solution_ids;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    sets.resize(m);
    for (int i = 0; i < m; ++i) {
        sets[i].id = i + 1;
        cin >> sets[i].cost;
        sets[i].mask.reset();
    }

    // Read element coverage info
    // For each element i from 1 to n
    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int set_id;
            cin >> set_id;
            // Map 1-based set ID to 0-based index
            if (set_id >= 1 && set_id <= m) {
                sets[set_id - 1].mask.set(i - 1);
            }
        }
    }

    // Timer setup
    auto start_time = chrono::steady_clock::now();
    // Use a time-based seed for randomness
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Main optimization loop
    while (true) {
        // Time check: allow margin before 10s limit
        auto curr_time = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(curr_time - start_time).count();
        if (elapsed > 9.8) break;

        // 1. Randomized Costs
        // Perturb costs to explore different greedy solutions
        vector<double> adj_costs(m);
        for(int i = 0; i < m; ++i) {
            double factor = uniform_real_distribution<double>(0.4, 1.6)(rng);
            adj_costs[i] = (double)sets[i].cost * factor + uniform_real_distribution<double>(0, 1e-6)(rng);
        }

        // 2. Greedy Construction
        bitset<MAXN> current_covered;
        current_covered.reset();
        vector<int> solution_indices;
        int covered_count = 0;
        
        while (covered_count < n) {
            int best_idx = -1;
            double best_score = 1e18; // Minimize cost per new element

            // Calculate needed elements
            bitset<MAXN> needed = ~current_covered;

            for (int i = 0; i < m; ++i) {
                // Calculate intersection of set i with needed elements
                bitset<MAXN> gain_mask = sets[i].mask & needed;
                int gain = gain_mask.count();

                if (gain > 0) {
                    double score = adj_costs[i] / gain;
                    if (score < best_score) {
                        best_score = score;
                        best_idx = i;
                    }
                }
            }

            if (best_idx == -1) {
                // Should not happen if a valid cover exists
                break;
            }

            solution_indices.push_back(best_idx);
            current_covered |= sets[best_idx].mask;
            covered_count = current_covered.count();
        }

        if (covered_count < n) continue; // Incomplete solution

        // 3. Pruning (Redundant Removal)
        // Sort selected sets by original cost descending.
        // We try to remove expensive sets if they are redundant.
        sort(solution_indices.begin(), solution_indices.end(), [&](int a, int b) {
            return sets[a].cost > sets[b].cost;
        });

        // Compute coverage counts for each element
        vector<int> cover_counts(n, 0);
        for (int idx : solution_indices) {
            for (int i = 0; i < n; ++i) {
                if (sets[idx].mask.test(i)) cover_counts[i]++;
            }
        }

        vector<int> pruned_solution;
        long long pruned_cost = 0;
        vector<bool> keep(m, false);
        for (int idx : solution_indices) keep[idx] = true;

        for (int idx : solution_indices) {
            bool can_remove = true;
            // A set is redundant if all its covered elements are covered by at least 2 sets
            for (int i = 0; i < n; ++i) {
                if (sets[idx].mask.test(i)) {
                    if (cover_counts[i] <= 1) {
                        can_remove = false;
                        break;
                    }
                }
            }

            if (can_remove) {
                keep[idx] = false;
                for (int i = 0; i < n; ++i) {
                    if (sets[idx].mask.test(i)) cover_counts[i]--;
                }
            }
        }

        // Collect finalized solution
        for (int i = 0; i < m; ++i) {
            if (keep[i]) {
                pruned_solution.push_back(i);
                pruned_cost += sets[i].cost;
            }
        }

        // 4. Update Global Best
        if (best_total_cost == -1 || pruned_cost < best_total_cost) {
            best_total_cost = pruned_cost;
            best_solution_ids.clear();
            for (int idx : pruned_solution) {
                best_solution_ids.push_back(sets[idx].id);
            }
        }
    }

    // Output
    if (best_total_cost != -1) {
        cout << best_solution_ids.size() << "\n";
        for (size_t i = 0; i < best_solution_ids.size(); ++i) {
            cout << best_solution_ids[i] << (i == best_solution_ids.size() - 1 ? "" : " ");
        }
        cout << "\n";
    } else {
        // Fallback if no solution found (should imply impossible input)
        cout << "0\n\n";
    }

    return 0;
}