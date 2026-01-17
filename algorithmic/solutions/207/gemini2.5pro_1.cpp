#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <set>
#include <algorithm>

using namespace std;

// Helper to perform a swap on S and update all related data structures
void perform_swap(int u, int v, vector<int>& s, vector<int>& pos, set<int>& misplaced_indices) {
    if (u == v) return;

    int val_u = s[u];
    int val_v = s[v];

    // Determine misplaced status changes before the swap
    bool u_misplaced_before = (s[u] != u);
    bool v_misplaced_before = (s[v] != v);
    bool u_misplaced_after = (val_v != u);
    bool v_misplaced_after = (val_u != v);

    // Update misplaced_indices for u
    if (u_misplaced_before && !u_misplaced_after) {
        misplaced_indices.erase(u);
    } else if (!u_misplaced_before && u_misplaced_after) {
        misplaced_indices.insert(u);
    }

    // Update misplaced_indices for v
    if (v_misplaced_before && !v_misplaced_after) {
        misplaced_indices.erase(v);
    } else if (!v_misplaced_before && v_misplaced_after) {
        misplaced_indices.insert(v);
    }

    // Perform the swap on s and pos
    swap(s[u], s[v]);
    swap(pos[val_u], pos[val_v]);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> s(n);
    vector<int> pos(n);
    set<int> misplaced_indices;
    for (int i = 0; i < n; ++i) {
        cin >> s[i];
        pos[s[i]] = i;
        if (s[i] != i) {
            misplaced_indices.insert(i);
        }
    }

    int m;
    cin >> m;

    vector<pair<int, int>> jerry_swaps(m);
    for (int i = 0; i < m; ++i) {
        cin >> jerry_swaps[i].first >> jerry_swaps[i].second;
    }

    int best_r = -1;
    unsigned long long best_v = -1; 
    vector<pair<int, int>> best_my_swaps;

    vector<pair<int, int>> current_my_swaps;
    long long current_total_dist = 0;

    if (misplaced_indices.empty()) {
        best_r = 0;
        best_v = 0;
    }

    for (int k = 0; k < m; ++k) {
        // Jerry's Move
        int x = jerry_swaps[k].first;
        int y = jerry_swaps[k].second;
        perform_swap(x, y, s, pos, misplaced_indices);

        // Your Move
        int u, v;
        if (misplaced_indices.empty()) {
            u = 0;
            v = 0;
        } else {
            int i = *misplaced_indices.begin();
            u = i;
            v = pos[i];
        }
        
        current_my_swaps.push_back({u, v});
        current_total_dist += abs(u - v);
        
        perform_swap(u, v, s, pos, misplaced_indices);

        if (misplaced_indices.empty()) {
            int r = k + 1;
            unsigned long long v_val = (unsigned long long)r * current_total_dist;
            if (best_r == -1 || v_val < best_v) {
                best_v = v_val;
                best_r = r;
                best_my_swaps = current_my_swaps;
            }
        }
    }

    cout << best_r << "\n";
    for (int i = 0; i < best_r; ++i) {
        cout << best_my_swaps[i].first << " " << best_my_swaps[i].second << "\n";
    }
    cout << best_v << "\n";

    return 0;
}