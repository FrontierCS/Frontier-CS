#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

const ll INF = 1e18;

struct Node {
    ll max_dp;
    ll min_a;
    ll max_a;
};

int n, m;
ll c;
vector<ll> a, b;
vector<ll> A, B;
vector<ll> dp;
vector<Node> tree;

// Build the segment tree. 
// The tree stores dp values for indices 0 to n.
// Initially dp values are -INF.
// We also store min_a and max_a for the range of indices covered by the node.
void build(int node, int start, int end) {
    if (start == end) {
        tree[node] = {-INF, A[start], A[start]};
    } else {
        int mid = (start + end) / 2;
        build(2 * node, start, mid);
        build(2 * node + 1, mid + 1, end);
        tree[node].max_dp = -INF;
        tree[node].min_a = tree[2 * node].min_a;
        tree[node].max_a = tree[2 * node + 1].max_a;
    }
}

// Update the dp value at index idx.
void update(int node, int start, int end, int idx, ll val) {
    if (start == end) {
        tree[node].max_dp = val;
        return;
    }
    int mid = (start + end) / 2;
    if (idx <= mid) update(2 * node, start, mid, idx, val);
    else update(2 * node + 1, mid + 1, end, idx, val);
    tree[node].max_dp = max(tree[2 * node].max_dp, tree[2 * node + 1].max_dp);
}

// Query the tree for max(dp[j] + rank(A[curr] - A[j])).
// k_min and k_max are the bounds on the possible rank values for the current node.
// This allows us to prune the search space for ranks.
ll query(int node, int start, int end, ll a_curr, int k_min, int k_max) {
    // If no valid dp value in this subtree, return -INF
    if (tree[node].max_dp == -INF) return -INF;
    
    ll diff_min = a_curr - tree[node].max_a;
    ll diff_max = a_curr - tree[node].min_a;

    // Find the rank for the smallest diff in this range
    // Rank is the largest k such that B[k] <= diff.
    // We restrict search to [k_min, k_max + 1] range in B.
    auto it_min = upper_bound(B.begin() + k_min, B.begin() + min((int)B.size(), k_max + 2), diff_min);
    int r_min = (int)(it_min - B.begin()) - 1;
    
    // Find the rank for the largest diff in this range
    auto it_max = upper_bound(B.begin() + k_min, B.begin() + min((int)B.size(), k_max + 2), diff_max);
    int r_max = (int)(it_max - B.begin()) - 1;
    
    // If the rank is constant for all j in this node's range, return result immediately
    if (r_min == r_max) {
        return tree[node].max_dp + r_min;
    }
    
    // If leaf node, diff_min == diff_max so r_min == r_max, handled above.
    
    int mid = (start + end) / 2;
    // Recurse with narrowed rank bounds [r_min, r_max]
    return max(query(2 * node, start, mid, a_curr, r_min, r_max),
               query(2 * node + 1, mid + 1, end, a_curr, r_min, r_max));
}

void solve() {
    if (!(cin >> n >> m >> c)) return;
    
    a.resize(n);
    A.resize(n + 1);
    A[0] = 0;
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        A[i + 1] = A[i] + a[i];
    }
    
    b.resize(m);
    B.resize(m + 1);
    B[0] = 0;
    for (int i = 0; i < m; ++i) {
        cin >> b[i];
        B[i + 1] = B[i] + b[i];
    }
    
    tree.resize(4 * (n + 1));
    build(1, 0, n);
    
    dp.resize(n + 1);
    dp[0] = 0;
    
    // Base case: day 0 has dp[0] = 0
    update(1, 0, n, 0, dp[0]);
    
    for (int i = 1; i <= n; ++i) {
        // Calculate dp[i] = max_{0<=j<i} (dp[j] + rank(A[i] - A[j])) - c
        ll val = query(1, 0, n, A[i], 0, m);
        dp[i] = val - c;
        update(1, 0, n, i, dp[i]);
    }
    
    cout << dp[n] << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}