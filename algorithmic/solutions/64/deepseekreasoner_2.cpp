#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

struct Item {
    ll val;
    int idx;
    bool operator<(const Item& other) const {
        return val > other.val; // descending
    }
};

int n;
ll T;
vector<Item> items;
vector<ll> suffix;
ll best_error;
vector<bool> best_subset; // in original order
ll total_sum;
chrono::steady_clock::time_point start_time;
const double TIME_LIMIT = 0.9; // seconds
bool found_perfect = false;

void update_best(ll error, const vector<bool>& cur_subset_sorted) {
    if (error < best_error) {
        best_error = error;
        fill(best_subset.begin(), best_subset.end(), false);
        for (int i = 0; i < n; ++i) {
            if (cur_subset_sorted[i]) {
                best_subset[items[i].idx] = true;
            }
        }
    }
}

inline bool time_is_up() {
    auto now = chrono::steady_clock::now();
    double elapsed = chrono::duration<double>(now - start_time).count();
    return elapsed > TIME_LIMIT;
}

void dfs(int i, ll cur_sum, vector<bool>& cur_subset_sorted) {
    if (found_perfect || best_error == 0) return;
    if (i % 10 == 0 && time_is_up()) return;

    if (i == n) {
        ll error = llabs(cur_sum - T);
        if (error < best_error) {
            update_best(error, cur_subset_sorted);
            if (error == 0) found_perfect = true;
        }
        return;
    }

    // Perfect sum found?
    if (cur_sum == T) {
        update_best(0, cur_subset_sorted);
        found_perfect = true;
        return;
    }

    // Pruning: compute achievable interval and its distance to T
    ll min_achievable = cur_sum;
    ll max_achievable = cur_sum + suffix[i];
    ll dist;
    if (T < min_achievable)
        dist = min_achievable - T;
    else if (T > max_achievable)
        dist = T - max_achievable;
    else
        dist = 0;
    if (dist >= best_error) return;

    // Heuristic ordering of branches
    if (cur_sum < T) {
        // try include first
        cur_subset_sorted[i] = true;
        dfs(i + 1, cur_sum + items[i].val, cur_subset_sorted);
        cur_subset_sorted[i] = false;
        dfs(i + 1, cur_sum, cur_subset_sorted);
    } else {
        // cur_sum >= T
        dfs(i + 1, cur_sum, cur_subset_sorted);
        cur_subset_sorted[i] = true;
        dfs(i + 1, cur_sum + items[i].val, cur_subset_sorted);
        cur_subset_sorted[i] = false;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> T;
    items.resize(n);
    total_sum = 0;
    for (int i = 0; i < n; ++i) {
        ll x;
        cin >> x;
        items[i] = {x, i};
        total_sum += x;
    }

    // sort descending to improve pruning
    sort(items.begin(), items.end());

    // suffix sums
    suffix.assign(n, 0);
    for (int i = n - 1; i >= 0; --i)
        suffix[i] = items[i].val + (i + 1 < n ? suffix[i + 1] : 0);

    // initialize best solution with empty and full subsets
    best_subset.resize(n, false);
    best_error = llabs(T); // empty subset
    if (llabs(total_sum - T) < best_error) {
        best_error = llabs(total_sum - T);
        fill(best_subset.begin(), best_subset.end(), true);
    }

    // greedy from below (take while sum <= T)
    vector<bool> greedy_sorted(n, false);
    ll sum_below = 0;
    for (int i = 0; i < n; ++i) {
        if (sum_below + items[i].val <= T) {
            sum_below += items[i].val;
            greedy_sorted[i] = true;
        }
    }
    ll error_below = llabs(sum_below - T);
    if (error_below < best_error)
        update_best(error_below, greedy_sorted);

    // greedy from above (add first not-taken item)
    if (sum_below < total_sum) {
        for (int i = 0; i < n; ++i) {
            if (!greedy_sorted[i]) {
                greedy_sorted[i] = true;
                sum_below += items[i].val;
                break;
            }
        }
        ll error_above = llabs(sum_below - T);
        if (error_above < best_error)
            update_best(error_above, greedy_sorted);
    }

    // start DFS with branch and bound
    start_time = chrono::steady_clock::now();
    vector<bool> cur_subset_sorted(n, false);
    dfs(0, 0, cur_subset_sorted);

    // output binary string
    for (int i = 0; i < n; ++i)
        cout << (best_subset[i] ? '1' : '0');
    cout << '\n';

    return 0;
}