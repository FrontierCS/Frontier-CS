#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <set>
#include <algorithm>

using namespace std;

// State for simulation
vector<int> S_sim;
vector<int> pos_sim;
set<pair<int, int>> cost_set; // Stores { |val - pos[val]|, val }

// Helper to remove a value's cost from the set if it's misplaced
void remove_from_cost_set(int val) {
    if (pos_sim[val] != val) {
        cost_set.erase({abs(val - pos_sim[val]), val});
    }
}

// Helper to add a value's cost to the set if it's misplaced
void add_to_cost_set(int val) {
    if (pos_sim[val] != val) {
        cost_set.insert({abs(val - pos_sim[val]), val});
    }
}

// Applies a swap on indices u, v to the global simulation state
void apply_swap_sim(int u, int v) {
    if (u == v) return;

    int val_u = S_sim[u];
    int val_v = S_sim[v];

    remove_from_cost_set(val_u);
    remove_from_cost_set(val_v);

    swap(S_sim[u], S_sim[v]);
    swap(pos_sim[val_u], pos_sim[val_v]);

    add_to_cost_set(val_u);
    add_to_cost_set(val_v);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    cin >> N;

    vector<int> S_initial(N);
    bool initially_sorted = true;
    for (int i = 0; i < N; ++i) {
        cin >> S_initial[i];
        if (S_initial[i] != i) {
            initially_sorted = false;
        }
    }

    int M;
    cin >> M;
    vector<pair<int, int>> jerry_swaps(M);
    for (int i = 0; i < M; ++i) {
        cin >> jerry_swaps[i].first >> jerry_swaps[i].second;
    }

    if (initially_sorted) {
        cout << 0 << endl;
        cout << 0 << endl;
        return 0;
    }

    // --- Simulation ---
    S_sim.resize(N);
    pos_sim.resize(N);

    // Initialize state
    S_sim = S_initial;
    for (int i = 0; i < N; ++i) {
        pos_sim[S_sim[i]] = i;
    }
    for (int i = 0; i < N; ++i) {
        if (pos_sim[i] != i) {
            cost_set.insert({abs(i - pos_sim[i]), i});
        }
    }

    vector<pair<int, int>> my_swaps(M);
    vector<long long> costs(M);
    vector<bool> is_sorted_at_round(M);

    for (int k = 0; k < M; ++k) {
        // Jerry's move
        apply_swap_sim(jerry_swaps[k].first, jerry_swaps[k].second);

        // My move
        if (cost_set.empty()) {
            my_swaps[k] = {0, 0};
            costs[k] = 0;
        } else {
            auto best = *cost_set.begin();
            int val_to_fix = best.second;
            int u = pos_sim[val_to_fix];
            int v = val_to_fix;
            
            my_swaps[k] = {u, v};
            costs[k] = best.first;

            apply_swap_sim(u, v);
        }

        is_sorted_at_round[k] = cost_set.empty();
    }

    // --- Find best R ---
    vector<long long> prefix_costs(M);
    if (M > 0) {
        prefix_costs[0] = costs[0];
        for (int k = 1; k < M; ++k) {
            prefix_costs[k] = prefix_costs[k - 1] + costs[k];
        }
    }
    
    long long min_V = -1;
    int best_R = -1;

    for (int R = 1; R <= M; ++R) {
        if (is_sorted_at_round[R - 1]) {
            long long current_V = (long long)R * prefix_costs[R - 1];
            if (best_R == -1 || current_V < min_V) {
                min_V = current_V;
                best_R = R;
            }
        }
    }
    
    // --- Output ---
    cout << best_R << endl;
    for (int k = 0; k < best_R; ++k) {
        cout << my_swaps[k].first << " " << my_swaps[k].second << endl;
    }
    cout << min_V << endl;

    return 0;
}