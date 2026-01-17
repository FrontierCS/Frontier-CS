#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <set>
#include <algorithm>

using namespace std;

// Helper to update DS when a value's position changes
void update_ds(int val, int old_pos, int new_pos, set<pair<int, int>>& ds) {
    if (old_pos != val) {
        ds.erase({abs(val - old_pos), val});
    }
    if (new_pos != val) {
        ds.insert({abs(val - new_pos), val});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> s(n);
    vector<int> pos(n);
    for (int i = 0; i < n; ++i) {
        cin >> s[i];
        pos[s[i]] = i;
    }

    int m;
    cin >> m;
    vector<pair<int, int>> jerry_swaps(m);
    for (int i = 0; i < m; ++i) {
        cin >> jerry_swaps[i].first >> jerry_swaps[i].second;
    }

    vector<int> s_sim = s;
    vector<int> pos_sim = pos;
    set<pair<int, int>> ds;
    for (int i = 0; i < n; ++i) {
        if (pos_sim[i] != i) {
            ds.insert({abs(i - pos_sim[i]), i});
        }
    }

    vector<long long> costs(m);
    vector<bool> is_sorted_after(m);
    vector<pair<int, int>> my_swaps_log(m);

    for (int k = 0; k < m; ++k) {
        // Jerry's move
        int x = jerry_swaps[k].first;
        int y = jerry_swaps[k].second;

        if (x != y) {
            int val_x = s_sim[x];
            int val_y = s_sim[y];
            
            update_ds(val_x, x, y, ds);
            update_ds(val_y, y, x, ds);
            
            swap(s_sim[x], s_sim[y]);
            pos_sim[val_x] = y;
            pos_sim[val_y] = x;
        }

        // My move
        if (ds.empty()) {
            my_swaps_log[k] = {0, 0};
            costs[k] = 0;
        } else {
            int val_to_fix = ds.begin()->second;
            int u = pos_sim[val_to_fix];
            int v = val_to_fix;

            my_swaps_log[k] = {u, v};
            costs[k] = abs(u - v);

            int val_at_v = s_sim[v];

            update_ds(val_to_fix, u, v, ds);
            update_ds(val_at_v, v, u, ds);

            swap(s_sim[u], s_sim[v]);
            pos_sim[val_to_fix] = v;
            pos_sim[val_at_v] = u;
        }
        is_sorted_after[k] = ds.empty();
    }

    // Find best R
    int best_r = -1;
    long long best_v = -1;

    // Check R=0 case
    bool initially_sorted = true;
    for(int i=0; i<n; ++i) {
        if (s[i] != i) {
            initially_sorted = false;
            break;
        }
    }
    if (initially_sorted) {
        best_r = 0;
        best_v = 0;
    }

    vector<long long> cost_prefix_sum(m, 0);
    if (m > 0) {
        cost_prefix_sum[0] = costs[0];
        for (int i = 1; i < m; ++i) {
            cost_prefix_sum[i] = cost_prefix_sum[i-1] + costs[i];
        }
    }

    for (int k = 0; k < m; ++k) {
        if (is_sorted_after[k]) {
            long long current_r = k + 1;
            long long current_total_cost = cost_prefix_sum[k];
            long long current_v = current_r * current_total_cost;
            if (best_r == -1 || current_v < best_v) {
                best_v = current_v;
                best_r = current_r;
            }
        }
    }

    cout << best_r << endl;
    
    for (int k = 0; k < best_r; ++k) {
        cout << my_swaps_log[k].first << " " << my_swaps_log[k].second << "\n";
    }
    
    cout << best_v << endl;

    return 0;
}