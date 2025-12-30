#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <functional>
#include <climits>
#include <numeric>
using namespace std;

const int MAX_N = 400;
const int MAX_M = 4000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<int> cost(m);
    for (int i = 0; i < m; ++i) {
        cin >> cost[i];
    }

    vector<vector<int>> elem_sets(n);
    vector<bitset<MAX_N>> set_bits(m);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        elem_sets[i].resize(k);
        for (int j = 0; j < k; ++j) {
            int a;
            cin >> a;
            --a; // convert to 0-indexed
            elem_sets[i][j] = a;
            set_bits[a].set(i);
        }
    }

    // ---------- Preprocessing: essential sets ----------
    bitset<MAX_N> covered_essential;
    vector<int> essential;
    vector<bool> set_taken(m, false);
    bool changed = true;
    while (changed) {
        changed = false;
        for (int e = 0; e < n; ++e) {
            if (covered_essential[e]) continue;
            int cnt = 0;
            int forced_set = -1;
            for (int s : elem_sets[e]) {
                if (!set_taken[s]) {
                    ++cnt;
                    forced_set = s;
                }
            }
            if (cnt == 1) {
                if (!set_taken[forced_set]) {
                    set_taken[forced_set] = true;
                    essential.push_back(forced_set);
                    covered_essential |= set_bits[forced_set];
                    changed = true;
                }
            }
        }
    }

    // Check feasibility
    bool feasible = true;
    for (int e = 0; e < n; ++e) {
        if (covered_essential[e]) continue;
        int cnt = 0;
        for (int s : elem_sets[e]) {
            if (!set_taken[s]) ++cnt;
        }
        if (cnt == 0) {
            feasible = false;
            break;
        }
    }
    if (!feasible) {
        cout << "0\n";
        return 0;
    }

    // ---------- Build reduced sets (not taken) ----------
    vector<int> reduced_orig_idx;
    vector<int> reduced_cost;
    vector<bitset<MAX_N>> reduced_bits;
    bitset<MAX_N> uncovered_mask = ~covered_essential;

    for (int s = 0; s < m; ++s) {
        if (set_taken[s]) continue;
        bitset<MAX_N> masked = set_bits[s] & uncovered_mask;
        if (masked.none()) continue; // useless set
        reduced_orig_idx.push_back(s);
        reduced_cost.push_back(cost[s]);
        reduced_bits.push_back(set_bits[s]); // keep full bitset
    }
    int reduced_m = reduced_orig_idx.size();

    // ---------- Dominance reduction ----------
    vector<bitset<MAX_N>> masked_bits(reduced_m);
    for (int i = 0; i < reduced_m; ++i) {
        masked_bits[i] = reduced_bits[i] & uncovered_mask;
    }

    vector<int> sorted_indices(reduced_m);
    iota(sorted_indices.begin(), sorted_indices.end(), 0);
    sort(sorted_indices.begin(), sorted_indices.end(),
         [&](int a, int b) {
             if (reduced_cost[a] != reduced_cost[b])
                 return reduced_cost[a] < reduced_cost[b];
             return masked_bits[a].count() > masked_bits[b].count();
         });

    vector<int> non_dominated;
    for (int idx : sorted_indices) {
        bool dominated = false;
        for (int nd : non_dominated) {
            if ((masked_bits[idx] & masked_bits[nd]) == masked_bits[idx] &&
                reduced_cost[nd] <= reduced_cost[idx]) {
                dominated = true;
                break;
            }
        }
        if (!dominated) {
            // remove any in non_dominated dominated by idx
            vector<int> new_non_dominated;
            for (int nd : non_dominated) {
                if (!((masked_bits[nd] & masked_bits[idx]) == masked_bits[nd] &&
                      reduced_cost[idx] <= reduced_cost[nd])) {
                    new_non_dominated.push_back(nd);
                }
            }
            new_non_dominated.push_back(idx);
            non_dominated = move(new_non_dominated);
        }
    }

    // Rebuild reduced sets from non_dominated
    vector<int> new_reduced_orig_idx;
    vector<int> new_reduced_cost;
    vector<bitset<MAX_N>> new_reduced_bits;
    for (int nd : non_dominated) {
        new_reduced_orig_idx.push_back(reduced_orig_idx[nd]);
        new_reduced_cost.push_back(reduced_cost[nd]);
        new_reduced_bits.push_back(reduced_bits[nd]);
    }
    reduced_orig_idx.swap(new_reduced_orig_idx);
    reduced_cost.swap(new_reduced_cost);
    reduced_bits.swap(new_reduced_bits);
    reduced_m = reduced_orig_idx.size();

    // ---------- Build element->reduced sets lists ----------
    vector<vector<int>> elem_reduced_sets(n);
    for (int e = 0; e < n; ++e) {
        if (covered_essential[e]) continue;
        for (int i = 0; i < reduced_m; ++i) {
            if (reduced_bits[i][e]) {
                elem_reduced_sets[e].push_back(i);
            }
        }
        // sort by cost ascending
        sort(elem_reduced_sets[e].begin(), elem_reduced_sets[e].end(),
             [&](int a, int b) { return reduced_cost[a] < reduced_cost[b]; });
    }

    // ---------- Greedy initial solution ----------
    int essential_cost = 0;
    for (int s : essential) essential_cost += cost[s];

    bitset<MAX_N> greedy_covered = covered_essential;
    vector<bool> greedy_used(reduced_m, false);
    int greedy_total_cost = essential_cost;
    vector<int> greedy_chosen;

    while (true) {
        int best_set = -1;
        double best_ratio = 1e18;
        for (int i = 0; i < reduced_m; ++i) {
            if (greedy_used[i]) continue;
            bitset<MAX_N> cover = reduced_bits[i] & ~greedy_covered;
            int cnt = cover.count();
            if (cnt == 0) continue;
            double ratio = reduced_cost[i] / (double)cnt;
            if (ratio < best_ratio) {
                best_ratio = ratio;
                best_set = i;
            }
        }
        if (best_set == -1) break;
        greedy_used[best_set] = true;
        greedy_chosen.push_back(best_set);
        greedy_covered |= reduced_bits[best_set];
        greedy_total_cost += reduced_cost[best_set];
    }

    // Check if greedy covered all
    bool all_covered = true;
    for (int e = 0; e < n; ++e) {
        if (!greedy_covered[e]) {
            all_covered = false;
            break;
        }
    }
    if (!all_covered) {
        greedy_total_cost = INT_MAX;
    }

    // Global best solution
    int best_cost = greedy_total_cost;
    vector<int> best_solution = essential;
    for (int idx : greedy_chosen) {
        best_solution.push_back(reduced_orig_idx[idx]);
    }

    // ---------- Branch and Bound ----------
    vector<bool> chosen_set(reduced_m, false);
    vector<int> cur_chosen;
    bitset<MAX_N> start_covered = covered_essential;

    function<void(int, bitset<MAX_N>)> dfs = [&](int cur_cost, bitset<MAX_N> cur_covered) {
        if (cur_cost >= best_cost) return;
        if (cur_covered.all()) {
            if (cur_cost < best_cost) {
                best_cost = cur_cost;
                best_solution.clear();
                for (int s : essential) best_solution.push_back(s);
                for (int idx : cur_chosen) best_solution.push_back(reduced_orig_idx[idx]);
            }
            return;
        }

        // Lower bound computation
        bitset<MAX_N> uncovered = ~cur_covered;
        int uncovered_count = uncovered.count();
        long long best_num = 1, best_den = 0;
        bool found = false;
        for (int i = 0; i < reduced_m; ++i) {
            if (chosen_set[i]) continue;
            bitset<MAX_N> cover = reduced_bits[i] & uncovered;
            int cnt = cover.count();
            if (cnt == 0) continue;
            if (!found) {
                best_num = reduced_cost[i];
                best_den = cnt;
                found = true;
            } else {
                if (reduced_cost[i] * best_den < best_num * cnt) {
                    best_num = reduced_cost[i];
                    best_den = cnt;
                }
            }
        }
        if (!found) return; // infeasible
        long long lb = cur_cost + (uncovered_count * best_num + best_den - 1) / best_den;
        if (lb >= best_cost) return;

        // Choose uncovered element with smallest degree
        int best_e = -1;
        int min_degree = INT_MAX;
        for (int e = 0; e < n; ++e) {
            if (cur_covered[e]) continue;
            int degree = 0;
            for (int s : elem_reduced_sets[e]) {
                if (!chosen_set[s]) ++degree;
            }
            if (degree < min_degree) {
                min_degree = degree;
                best_e = e;
            }
        }
        if (best_e == -1) return;

        // Branch on sets covering best_e
        for (int s : elem_reduced_sets[best_e]) {
            if (chosen_set[s]) continue;
            if (cur_cost + reduced_cost[s] >= best_cost) continue;
            bitset<MAX_N> new_covered = cur_covered | reduced_bits[s];
            chosen_set[s] = true;
            cur_chosen.push_back(s);
            dfs(cur_cost + reduced_cost[s], new_covered);
            cur_chosen.pop_back();
            chosen_set[s] = false;
        }
    };

    dfs(essential_cost, start_covered);

    // Output solution
    cout << best_solution.size() << "\n";
    for (size_t i = 0; i < best_solution.size(); ++i) {
        if (i > 0) cout << " ";
        cout << best_solution[i] + 1; // convert back to 1-indexed
    }
    cout << "\n";

    return 0;
}