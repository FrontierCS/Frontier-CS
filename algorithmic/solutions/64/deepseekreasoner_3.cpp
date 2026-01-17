#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll n, T;
vector<ll> a_sorted;
vector<int> orig_idx;
vector<ll> suffix;
ll best_error;
vector<bool> best_mask;
bool found_exact = false;

void update_best(ll sum, const vector<bool>& cur_mask) {
    ll error = llabs(T - sum);
    if (error < best_error) {
        best_error = error;
        for (int i = 0; i < n; ++i) {
            best_mask[orig_idx[i]] = cur_mask[i];
        }
        if (error == 0) found_exact = true;
    }
}

void dfs(int i, ll sum, vector<bool>& cur_mask) {
    if (found_exact) return;
    update_best(sum, cur_mask);
    if (i == n) return;

    ll rem = suffix[i];
    ll suffix_next = rem - a_sorted[i];

    // Option: not take a_sorted[i]
    ll min_none = sum;
    ll max_none = sum + suffix_next;
    ll best_none;
    if (T >= min_none && T <= max_none) {
        best_none = 0;
    } else {
        best_none = min(llabs(T - min_none), llabs(T - max_none));
    }

    // Option: take a_sorted[i]
    ll min_take = sum + a_sorted[i];
    ll max_take = sum + rem;
    ll best_take;
    if (T >= min_take && T <= max_take) {
        best_take = 0;
    } else {
        best_take = min(llabs(T - min_take), llabs(T - max_take));
    }

    if (best_none < best_error) {
        dfs(i+1, sum, cur_mask);
        if (found_exact) return;
    }
    if (best_take < best_error) {
        cur_mask[i] = true;
        dfs(i+1, sum + a_sorted[i], cur_mask);
        cur_mask[i] = false;
        if (found_exact) return;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> T;
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    vector<pair<ll, int>> items;
    for (int i = 0; i < n; ++i) {
        items.emplace_back(a[i], i);
    }
    sort(items.begin(), items.end(), greater<pair<ll, int>>());

    a_sorted.resize(n);
    orig_idx.resize(n);
    for (int i = 0; i < n; ++i) {
        a_sorted[i] = items[i].first;
        orig_idx[i] = items[i].second;
    }

    suffix.assign(n+1, 0);
    for (int i = n-1; i >= 0; --i) {
        suffix[i] = suffix[i+1] + a_sorted[i];
    }

    best_mask.assign(n, false);
    best_error = LLONG_MAX;

    vector<bool> mask1(n, false);
    ll sum1 = 0;
    for (int i = 0; i < n; ++i) {
        if (sum1 + a_sorted[i] <= T) {
            sum1 += a_sorted[i];
            mask1[i] = true;
        }
    }
    update_best(sum1, mask1);

    vector<bool> mask2(n, false);
    ll sum2 = 0;
    for (int i = 0; i < n; ++i) {
        if (llabs(T - (sum2 + a_sorted[i])) < llabs(T - sum2)) {
            sum2 += a_sorted[i];
            mask2[i] = true;
        }
    }
    update_best(sum2, mask2);

    if (!found_exact) {
        vector<bool> cur_mask(n, false);
        dfs(0, 0, cur_mask);
    }

    for (int i = 0; i < n; ++i) {
        cout << (best_mask[i] ? '1' : '0');
    }
    cout << '\n';

    return 0;
}