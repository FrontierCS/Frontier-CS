#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Op {
    int l, r;
};

// compute a hash for the permutation to detect cycles
ll compute_hash(const vector<int>& a) {
    ll hash = 0;
    const ll base = 1000003;
    const ll mod = (1LL << 61) - 1;
    for (size_t i = 1; i < a.size(); ++i) {
        hash = (hash * base + a[i]) % mod;
    }
    return hash;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<int> cur(n + 1);          // 1-indexed current permutation
    for (int i = 1; i <= n; ++i) cur[i] = a[i - 1];

    vector<pair<int, int>> ops_applied;   // recorded operations (l, r)

    // small n: use adjacent swaps (x = 1)
    if (n <= 3) {
        int x = 1;
        // bubble sort with adjacent reversals (length 2)
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j < n; ++j) {
                if (cur[j] > cur[j + 1]) {
                    swap(cur[j], cur[j + 1]);
                    ops_applied.push_back({j, j + 1});
                }
            }
        }
        cout << x << "\n";
        cout << ops_applied.size() << "\n";
        for (auto &p : ops_applied) {
            cout << p.first << " " << p.second << "\n";
        }
        return 0;
    }

    // n >= 4: choose x = n-1
    int x = n - 1;
    vector<Op> ops(4);
    ops[0] = {1, n};       // whole array reversal (length n)
    ops[1] = {1, n - 2};   // length n-2
    ops[2] = {2, n - 1};   // length n-2
    ops[3] = {3, n};       // length n-2

    // cost = breakpoints * BP_WEIGHT + sum of distances to correct position
    const int BP_WEIGHT = 100000;
    auto compute_cost = [&](const vector<int>& arr) -> ll {
        int breakpoints = 0;
        ll dist_sum = 0;
        for (int i = 1; i <= n; ++i) {
            if (arr[i] != i) ++breakpoints;
            dist_sum += abs(arr[i] - i);
        }
        return (ll)breakpoints * BP_WEIGHT + dist_sum;
    };

    unordered_set<ll> visited;
    ll cur_hash = compute_hash(cur);
    visited.insert(cur_hash);

    int steps = 0;
    const int max_steps = 200 * n;
    int best_breakpoints = n;
    int stagnation = 0;

    while (steps < max_steps) {
        // check if sorted
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (cur[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;

        // count current breakpoints
        int cur_bp = 0;
        for (int i = 1; i <= n; ++i) if (cur[i] != i) ++cur_bp;
        if (cur_bp < best_breakpoints) {
            best_breakpoints = cur_bp;
            stagnation = 0;
        } else {
            ++stagnation;
        }
        if (stagnation > 100) {
            visited.clear();
            stagnation = 0;
        }

        ll cur_cost = compute_cost(cur);
        int best_op = -1;
        ll best_cost = 1e18;
        vector<ll> next_hashes(4);
        vector<vector<int>> next_arrs(4);

        // evaluate each possible operation
        for (int idx = 0; idx < 4; ++idx) {
            vector<int> tmp = cur;
            int l = ops[idx].l, r = ops[idx].r;
            reverse(tmp.begin() + l, tmp.begin() + r + 1);
            ll cost = compute_cost(tmp);
            ll hash = compute_hash(tmp);
            next_hashes[idx] = hash;
            next_arrs[idx] = tmp;
            if (cost < best_cost) {
                best_cost = cost;
                best_op = idx;
            }
        }

        // choose the best operation that does not lead to a visited state
        int chosen = -1;
        for (int i = 0; i < 4; ++i) {
            int idx = (best_op + i) % 4;
            if (visited.find(next_hashes[idx]) == visited.end()) {
                chosen = idx;
                break;
            }
        }
        if (chosen == -1) {
            // all lead to visited states -> clear set and choose the best
            visited.clear();
            chosen = best_op;
        }

        // apply the chosen operation
        int l = ops[chosen].l, r = ops[chosen].r;
        reverse(cur.begin() + l, cur.begin() + r + 1);
        ops_applied.push_back({l, r});

        // update state
        cur_hash = next_hashes[chosen];
        visited.insert(cur_hash);
        if (visited.size() > 10000) visited.clear();

        ++steps;
    }

    cout << x << "\n";
    cout << ops_applied.size() << "\n";
    for (auto &p : ops_applied) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}