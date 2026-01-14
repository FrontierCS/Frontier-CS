#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const long long INF = -1e18; 

struct Node {
    long long max_val;
};

vector<long long> A;
vector<long long> B;
vector<long long> discrete_A;
vector<Node> seg_tree;
int N_seg;

void build(int node, int l, int r) {
    if (l > r) return;
    if (l == r) {
        seg_tree[node] = {INF};
        return;
    }
    int mid = l + (r - l) / 2;
    build(2 * node, l, mid);
    build(2 * node + 1, mid + 1, r);
    seg_tree[node].max_val = max(seg_tree[2 * node].max_val, seg_tree[2 * node + 1].max_val);
}

void update(int node, int l, int r, int pos, long long val) {
    if (l > r) return;
    if (l == r) {
        seg_tree[node].max_val = max(seg_tree[node].max_val, val);
        return;
    }
    int mid = l + (r - l) / 2;
    if (pos <= mid) {
        update(2 * node, l, mid, pos, val);
    } else {
        update(2 * node + 1, mid + 1, r, pos, val);
    }
    seg_tree[node].max_val = max(seg_tree[2 * node].max_val, seg_tree[2 * node + 1].max_val);
}

long long query(int node, int l, int r, int ql, int qr) {
    if (ql > qr || l > r || ql > r || qr < l) {
        return INF;
    }
    if (ql <= l && r <= qr) {
        return seg_tree[node].max_val;
    }
    int mid = l + (r - l) / 2;
    long long left_max = query(2 * node, l, mid, ql, qr);
    long long right_max = query(2 * node + 1, mid + 1, r, ql, qr);
    return max(left_max, right_max);
}

void solve() {
    int n, m;
    long long c;
    cin >> n >> m >> c;

    A.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        cin >> A[i];
    }
    for (int i = 1; i <= n; ++i) {
        A[i] += A[i - 1];
    }

    B.assign(m + 1, 0);
    for (int i = 1; i <= m; ++i) {
        cin >> B[i];
    }
    for (int i = 1; i <= m; ++i) {
        B[i] += B[i - 1];
    }
    B.push_back(4e12); // Sentinel for B_{m+1}

    discrete_A = A;
    sort(discrete_A.begin(), discrete_A.end());
    discrete_A.erase(unique(discrete_A.begin(), discrete_A.end()), discrete_A.end());
    
    N_seg = discrete_A.size();
    seg_tree.assign(4 * N_seg + 4, {INF});
    build(1, 0, N_seg - 1);
    
    vector<long long> dp(n + 1, INF);
    dp[0] = 0;

    auto get_pos = [&](long long val) {
        return lower_bound(discrete_A.begin(), discrete_A.end(), val) - discrete_A.begin();
    };

    int pos0 = get_pos(A[0]);
    update(1, 0, N_seg - 1, pos0, dp[0]);

    for (int i = 1; i <= n; ++i) {
        long long max_val = INF;
        for (int k = 0; k <= m; ++k) {
            long long required_exp_low = B[k];
            long long required_exp_high = B[k + 1];

            long long Aj_high = A[i] - required_exp_low;
            long long Aj_low = A[i] - required_exp_high;

            int pos_low = upper_bound(discrete_A.begin(), discrete_A.end(), Aj_low) - discrete_A.begin();
            int pos_high = upper_bound(discrete_A.begin(), discrete_A.end(), Aj_high) - discrete_A.begin() - 1;
            
            if (pos_low <= pos_high) {
                long long max_dp_j = query(1, 0, N_seg - 1, pos_low, pos_high);
                if (max_dp_j > INF + 100) {
                    max_val = max(max_val, max_dp_j + k - c);
                }
            }
        }
        dp[i] = max_val;
        int pos_i = get_pos(A[i]);
        if (dp[i] > INF + 100) {
            update(1, 0, N_seg - 1, pos_i, dp[i]);
        }
    }

    cout << dp[n] << "\n";
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