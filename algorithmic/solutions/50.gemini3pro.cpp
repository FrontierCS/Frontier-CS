#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <utility>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int N, M;
vector<long long> costs;
vector<vector<int>> elem_to_sets;
vector<vector<int>> set_to_elems;
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

struct Solution {
    vector<int> sets; // indices 0-based
    long long cost;
};

int main() {
    fast_io();
    auto start_time = chrono::steady_clock::now();

    if (!(cin >> N >> M)) return 0;

    costs.resize(M);
    for (int i = 0; i < M; ++i) cin >> costs[i];

    elem_to_sets.resize(N);
    set_to_elems.resize(M);

    for (int i = 0; i < N; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int s_id;
            cin >> s_id;
            --s_id; // convert to 0-based
            elem_to_sets[i].push_back(s_id);
            set_to_elems[s_id].push_back(i);
        }
    }

    Solution best_sol;
    best_sol.cost = -1;

    vector<int> current_sets;
    vector<bool> is_selected(M, false);
    vector<int> cover_count(N, 0);
    int num_covered = 0;
    long long current_cost = 0;
    vector<int> gain(M);

    // Initialize gains for all sets
    for (int i = 0; i < M; ++i) gain[i] = set_to_elems[i].size();

    // Initial Deterministic Greedy Construction
    while (num_covered < N) {
        int best_s = -1;
        double best_val = 1e18;
        // Find set minimizing cost / newly_covered
        for (int i = 0; i < M; ++i) {
            if (!is_selected[i] && gain[i] > 0) {
                double val = (double)costs[i] / gain[i];
                if (val < best_val) {
                    best_val = val;
                    best_s = i;
                }
            }
        }

        if (best_s == -1) break; // Should not happen given problem constraints

        // Add set
        is_selected[best_s] = true;
        current_sets.push_back(best_s);
        current_cost += costs[best_s];
        
        // Update coverage and gains
        for (int e : set_to_elems[best_s]) {
            if (cover_count[e] == 0) {
                num_covered++;
                // Element e is now covered, so other sets covering it lose potential gain
                for (int s : elem_to_sets[e]) gain[s]--;
            }
            cover_count[e]++;
        }
    }

    // Prune Function: Removes redundant sets
    auto run_prune = [&]() {
        // Sort by cost descending to remove most expensive redundant sets first
        sort(current_sets.begin(), current_sets.end(), [&](int a, int b) {
            if (costs[a] != costs[b]) return costs[a] > costs[b];
            return a > b;
        });

        vector<int> kept;
        kept.reserve(current_sets.size());

        for (int s : current_sets) {
            bool needed = false;
            for (int e : set_to_elems[s]) {
                if (cover_count[e] == 1) {
                    needed = true;
                    break;
                }
            }
            if (needed) {
                kept.push_back(s);
            } else {
                // Remove redundant set
                current_cost -= costs[s];
                is_selected[s] = false;
                for (int e : set_to_elems[s]) {
                    cover_count[e]--;
                }
            }
        }
        current_sets = move(kept);
    };

    run_prune();

    best_sol.sets = current_sets;
    best_sol.cost = current_cost;

    uniform_real_distribution<double> dist_mul(0.7, 1.3);

    // Iterative Local Search (Destroy and Repair)
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::duration<double>>(curr_time - start_time).count() > 9.8) break;

        // Start each iteration from the best solution found so far (Iterated Greedy)
        current_sets = best_sol.sets;
        current_cost = best_sol.cost;
        
        fill(is_selected.begin(), is_selected.end(), false);
        for(int s : current_sets) is_selected[s] = true;
        
        fill(cover_count.begin(), cover_count.end(), 0);
        for(int s : current_sets) {
            for(int e : set_to_elems[s]) cover_count[e]++;
        }
        
        fill(gain.begin(), gain.end(), 0); // Since full cover, gains are 0
        num_covered = N;

        // 1. Destroy: Remove a random subset of sets
        int sz = current_sets.size();
        if (sz == 0) break;
        int remove_cnt = uniform_int_distribution<int>(1, max(1, sz / 3))(rng);

        for(int k=0; k<remove_cnt; ++k) {
             int idx = uniform_int_distribution<int>(0, current_sets.size() - 1)(rng);
             int s = current_sets[idx];
             
             is_selected[s] = false;
             current_cost -= costs[s];
             
             for (int e : set_to_elems[s]) {
                 cover_count[e]--;
                 if (cover_count[e] == 0) {
                     num_covered--;
                     // Element e becomes uncovered, sets covering it gain potential
                     for (int other : elem_to_sets[e]) {
                         if (!is_selected[other]) gain[other]++;
                     }
                 }
             }
             
             // Remove from vector
             current_sets[idx] = current_sets.back();
             current_sets.pop_back();
        }

        // 2. Repair: Randomized Greedy
        while (num_covered < N) {
            int best_s = -1;
            double best_val = 1e18;
            
            // Randomize score to explore different paths
            for (int i = 0; i < M; ++i) {
                if (!is_selected[i] && gain[i] > 0) {
                    double val = ((double)costs[i] / gain[i]) * dist_mul(rng);
                    if (val < best_val) {
                        best_val = val;
                        best_s = i;
                    }
                }
            }

            if (best_s == -1) break; 

            is_selected[best_s] = true;
            current_sets.push_back(best_s);
            current_cost += costs[best_s];

            for (int e : set_to_elems[best_s]) {
                if (cover_count[e] == 0) {
                    num_covered++;
                    for (int s : elem_to_sets[e]) gain[s]--;
                }
                cover_count[e]++;
            }
        }

        // 3. Prune
        run_prune();

        // 4. Update Best
        if (current_cost < best_sol.cost) {
            best_sol.cost = current_cost;
            best_sol.sets = current_sets;
        }
    }

    cout << best_sol.sets.size() << "\n";
    for (int i = 0; i < best_sol.sets.size(); ++i) {
        cout << best_sol.sets[i] + 1 << (i == best_sol.sets.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}