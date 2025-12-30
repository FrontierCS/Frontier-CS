#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const long long INF = -2e18; // Use a sufficiently small number for infinity

struct Node {
    long long max_val;
    long long lazy;
};

vector<long long> a_prefix;
vector<long long> b_prefix;
vector<long long> dp;
vector<Node> tree;

void build(int node, int start, int end) {
    tree[node].lazy = 0;
    if (start == end) {
        tree[node].max_val = (start == 0) ? 0 : INF;
        return;
    }
    int mid = (start + end) / 2;
    build(2 * node, start, mid);
    build(2 * node + 1, mid + 1, end);
    tree[node].max_val = max(tree[2 * node].max_val, tree[2 * node + 1].max_val);
}

void push(int node, int start, int end) {
    if (tree[node].lazy != 0 && start != end) {
        tree[2 * node].max_val += tree[node].lazy;
        tree[2 * node].lazy += tree[node].lazy;
        tree[2 * node + 1].max_val += tree[node].lazy;
        tree[2 * node + 1].lazy += tree[node].lazy;
        tree[node].lazy = 0;
    }
}

void range_add(int node, int start, int end, int l, int r, int val) {
    if (start > end || start > r || end < l) {
        return;
    }
    if (l <= start && end <= r) {
        tree[node].max_val += val;
        tree[node].lazy += val;
        return;
    }
    push(node, start, end);
    int mid = (start + end) / 2;
    range_add(2 * node, start, mid, l, r, val);
    range_add(2 * node + 1, mid + 1, end, l, r, val);
    tree[node].max_val = max(tree[2 * node].max_val, tree[2 * node + 1].max_val);
}

void point_update(int node, int start, int end, int idx, long long val) {
    if (start == end) {
        tree[node].max_val = val;
        tree[node].lazy = 0;
        return;
    }
    push(node, start, end);
    int mid = (start + end) / 2;
    if (start <= idx && idx <= mid) {
        point_update(2 * node, start, mid, idx, val);
    } else {
        point_update(2 * node + 1, mid + 1, end, idx, val);
    }
    tree[node].max_val = max(tree[2 * node].max_val, tree[2 * node + 1].max_val);
}

long long query_max(int node, int start, int end, int l, int r) {
    if (start > end || start > r || end < l) {
        return INF;
    }
    if (l <= start && end <= r) {
        return tree[node].max_val;
    }
    push(node, start, end);
    int mid = (start + end) / 2;
    long long p1 = query_max(2 * node, start, mid, l, r);
    long long p2 = query_max(2 * node + 1, mid + 1, end, l, r);
    return max(p1, p2);
}

void solve() {
    int n, m;
    long long c;
    cin >> n >> m >> c;

    a_prefix.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        long long val;
        cin >> val;
        a_prefix[i] = a_prefix[i - 1] + val;
    }

    b_prefix.assign(m + 1, 0);
    for (int i = 1; i <= m; ++i) {
        long long val;
        cin >> val;
        b_prefix[i] = b_prefix[i - 1] + val;
    }

    dp.assign(n + 1, 0);
    tree.assign(4 * (n + 1), {INF, 0});
    
    build(1, 0, n);

    for (int i = 1; i <= n; ++i) {
        if (a_prefix[i] > a_prefix[i - 1]) {
            for (int k = 1; k <= m; ++k) {
                long long threshold_high = a_prefix[i] - b_prefix[k];
                long long threshold_low = a_prefix[i - 1] - b_prefix[k];
                
                auto j_start_it = upper_bound(a_prefix.begin(), a_prefix.begin() + i, threshold_low);
                auto j_end_it = upper_bound(a_prefix.begin(), a_prefix.begin() + i, threshold_high);
                
                int j_start = j_start_it - a_prefix.begin();
                int j_end = (j_end_it - a_prefix.begin()) - 1;

                if (j_start <= j_end) {
                    range_add(1, 0, n, j_start, j_end, 1);
                }
            }
        }

        long long max_val = query_max(1, 0, n, 0, i - 1);
        dp[i] = max_val - c;
        point_update(1, 0, n, i, dp[i]);
    }

    cout << dp[n] << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}