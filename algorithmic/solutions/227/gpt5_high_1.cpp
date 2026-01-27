#include <bits/stdc++.h>
using namespace std;

static inline vector<int> get_monotone_subseq(const vector<int>& idx, const vector<int>& arr, bool increasing) {
    int m = (int)idx.size();
    vector<int> tail_vals;
    vector<int> tail_idx;
    tail_vals.reserve(m);
    tail_idx.reserve(m);
    vector<int> prev(m, -1);

    for (int k = 0; k < m; ++k) {
        int val = arr[idx[k]];
        if (!increasing) val = -val;
        auto it = lower_bound(tail_vals.begin(), tail_vals.end(), val);
        int pos = (int)(it - tail_vals.begin());
        if (it == tail_vals.end()) {
            tail_vals.push_back(val);
            tail_idx.push_back(k);
        } else {
            *it = val;
            tail_idx[pos] = k;
        }
        if (pos > 0) prev[k] = tail_idx[pos - 1];
    }

    vector<int> res;
    if (tail_idx.empty()) return res;
    int k = tail_idx.back();
    while (k != -1) {
        res.push_back(idx[k]);
        k = prev[k];
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // group types: 0->a (I), 1->b (D), 2->c (I), 3->d (D)
    bool is_inc[4] = {true, false, true, false};
    array<int,4> base = {0,1,2,3};

    long long best_sum = -1;
    array<int,4> best_order = base;

    // Evaluate all permutations of order
    array<int,4> ord = base;
    do {
        vector<int> alive(n);
        iota(alive.begin(), alive.end(), 0);
        vector<char> used(n, 0);
        long long total = 0;

        for (int t = 0; t < 4; ++t) {
            int g = ord[t];
            vector<int> selected = get_monotone_subseq(alive, p, is_inc[g]);
            total += (long long)selected.size();
            for (int idx : selected) used[idx] = 1;
            vector<int> new_alive;
            new_alive.reserve(alive.size());
            for (int idx : alive) if (!used[idx]) new_alive.push_back(idx);
            alive.swap(new_alive);
        }
        if (total > best_sum) {
            best_sum = total;
            best_order = ord;
        }
    } while (next_permutation(ord.begin(), ord.end()));

    // Re-run with best order to construct final assignment
    vector<int> alive(n);
    iota(alive.begin(), alive.end(), 0);
    vector<char> used(n, 0);
    vector<vector<int>> group_indices(4);
    for (int t = 0; t < 4; ++t) {
        int g = best_order[t];
        vector<int> selected = get_monotone_subseq(alive, p, is_inc[g]);
        for (int idx : selected) {
            used[idx] = 1;
            group_indices[g].push_back(idx);
        }
        vector<int> new_alive;
        new_alive.reserve(alive.size());
        for (int idx : alive) if (!used[idx]) new_alive.push_back(idx);
        alive.swap(new_alive);
    }
    // Assign leftover to group d (index 3)
    for (int idx : alive) group_indices[3].push_back(idx);

    // Build output sequences in order of appearance
    vector<vector<int>> groups_vals(4);
    groups_vals[0].reserve(group_indices[0].size());
    groups_vals[1].reserve(group_indices[1].size());
    groups_vals[2].reserve(group_indices[2].size());
    groups_vals[3].reserve(group_indices[3].size());

    // For safety, sort indices of each group (they should already be in order, but ensure)
    for (int g = 0; g < 4; ++g) {
        sort(group_indices[g].begin(), group_indices[g].end());
        for (int idx : group_indices[g]) groups_vals[g].push_back(p[idx]);
    }

    cout << groups_vals[0].size() << ' ' << groups_vals[1].size() << ' ' << groups_vals[2].size() << ' ' << groups_vals[3].size() << "\n";
    for (size_t i = 0; i < groups_vals[0].size(); ++i) {
        if (i) cout << ' ';
        cout << groups_vals[0][i];
    }
    cout << "\n";
    for (size_t i = 0; i < groups_vals[1].size(); ++i) {
        if (i) cout << ' ';
        cout << groups_vals[1][i];
    }
    cout << "\n";
    for (size_t i = 0; i < groups_vals[2].size(); ++i) {
        if (i) cout << ' ';
        cout << groups_vals[2][i];
    }
    cout << "\n";
    for (size_t i = 0; i < groups_vals[3].size(); ++i) {
        if (i) cout << ' ';
        cout << groups_vals[3][i];
    }
    cout << "\n";

    return 0;
}