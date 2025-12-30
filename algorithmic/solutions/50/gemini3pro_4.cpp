#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Maximum constraints based on problem statement
const int MAXN = 405;
const int MAXM = 4005;

// Problem data
int n, m;
long long costs[MAXM];
vector<int> elements_in_set[MAXM]; // Map set ID -> elements
vector<int> sets_covering[MAXN];   // Map element ID -> sets

// Current solution state
bool selected[MAXM];
int cover_count[MAXN];
long long current_cost = 0;
int uncovered_cnt = 0;

// Best solution found so far
long long best_total_cost = -1;
vector<int> best_set_indices;

// Random number generator for randomized greedy
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
uniform_real_distribution<double> dist(0.85, 1.25);

// Auxiliary arrays for efficient greedy step
int gains[MAXM];
int gain_gen[MAXM];
int cur_gen = 0;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= m; ++i) {
        cin >> costs[i];
    }

    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int s_id;
            cin >> s_id;
            sets_covering[i].push_back(s_id);
            elements_in_set[s_id].push_back(i);
        }
    }

    // Precompute sets that are mandatory (cover elements that no other set covers)
    vector<int> mandatory;
    for (int i = 1; i <= n; ++i) {
        if (sets_covering[i].size() == 1) {
            mandatory.push_back(sets_covering[i][0]);
        }
    }
    sort(mandatory.begin(), mandatory.end());
    mandatory.erase(unique(mandatory.begin(), mandatory.end()), mandatory.end());

    auto start_time = chrono::steady_clock::now();
    double time_limit = 9.8; // Time limit buffer

    // Pre-allocate vectors to avoid reallocation in loop
    vector<int> candidates;
    candidates.reserve(m);
    vector<int> current_sol;
    current_sol.reserve(m);

    // Iterative Randomized Greedy + Pruning
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration_cast<chrono::duration<double>>(curr_time - start_time).count() > time_limit) break;

        // Reset state
        for (int i = 1; i <= m; ++i) selected[i] = false;
        for (int i = 1; i <= n; ++i) cover_count[i] = 0;
        current_cost = 0;
        uncovered_cnt = n;

        // Force select mandatory sets
        for (int s : mandatory) {
            if (!selected[s]) {
                selected[s] = true;
                current_cost += costs[s];
                for (int elem : elements_in_set[s]) {
                    if (cover_count[elem] == 0) uncovered_cnt--;
                    cover_count[elem]++;
                }
            }
        }

        // Greedy construction
        while (uncovered_cnt > 0) {
            cur_gen++;
            candidates.clear();
            
            // Calculate gains (number of newly covered elements) only for relevant sets
            for (int i = 1; i <= n; ++i) {
                if (cover_count[i] == 0) {
                    if (sets_covering[i].empty()) {
                         // Impossible to cover this element
                         goto end_iteration;
                    }
                    for (int s : sets_covering[i]) {
                        if (!selected[s]) {
                            if (gain_gen[s] != cur_gen) {
                                gains[s] = 0;
                                gain_gen[s] = cur_gen;
                                candidates.push_back(s);
                            }
                            gains[s]++;
                        }
                    }
                }
            }

            if (candidates.empty()) goto end_iteration;

            int best_set = -1;
            double best_score = 1e18;

            // Pick the set with best (lowest) Cost/Gain ratio
            for (int s : candidates) {
                double score = (double)costs[s] / gains[s];
                // Random perturbation to explore different solutions
                score *= dist(rng);

                if (score < best_score) {
                    best_score = score;
                    best_set = s;
                }
            }

            if (best_set != -1) {
                selected[best_set] = true;
                current_cost += costs[best_set];
                for (int elem : elements_in_set[best_set]) {
                    if (cover_count[elem] == 0) uncovered_cnt--;
                    cover_count[elem]++;
                }
            } else {
                goto end_iteration;
            }
        }

        // Pruning (Reverse Delete)
        if (uncovered_cnt == 0) {
            current_sol.clear();
            for (int i = 1; i <= m; ++i) {
                if (selected[i]) current_sol.push_back(i);
            }

            // Try to remove most expensive sets first
            sort(current_sol.begin(), current_sol.end(), [](int a, int b) {
                return costs[a] > costs[b];
            });

            for (int s : current_sol) {
                // A set is redundant if all its elements are covered by at least 2 sets (including itself)
                bool redundant = true;
                for (int elem : elements_in_set[s]) {
                    if (cover_count[elem] == 1) {
                        redundant = false;
                        break;
                    }
                }
                
                if (redundant) {
                    selected[s] = false;
                    current_cost -= costs[s];
                    for (int elem : elements_in_set[s]) {
                        cover_count[elem]--;
                    }
                }
            }

            // Update global best
            if (best_total_cost == -1 || current_cost < best_total_cost) {
                best_total_cost = current_cost;
                best_set_indices.clear();
                for (int i = 1; i <= m; ++i) {
                    if (selected[i]) best_set_indices.push_back(i);
                }
            }
        }
        
        end_iteration:;
    }

    // Output result
    cout << best_set_indices.size() << "\n";
    for (size_t i = 0; i < best_set_indices.size(); ++i) {
        cout << best_set_indices[i] << (i == best_set_indices.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}