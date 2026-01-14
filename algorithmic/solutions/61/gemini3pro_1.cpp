#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

const ll INF = 1e18;

struct Point {
    ll x, y;
};

int n, m;
ll c;
vector<ll> a, b;
vector<ll> S, B;
vector<ll> dp;

// Helper function to solve queries using Divide & Conquer (monotonicity optimization)
void solve_queries(const vector<Point>& updates, const vector<int>& queries, int q_l, int q_r, int u_l, int u_r) {
    if (q_l > q_r) return;
    
    int q_mid = (q_l + q_r) / 2;
    int q_idx = queries[q_mid];
    ll budget = S[q_idx];
    
    int best_u = -1;
    ll max_val = -INF;
    
    int start_u = u_l;
    int end_u = u_r;
    
    for (int i = start_u; i <= end_u; ++i) {
        ll rem = budget - updates[i].x;
        if (rem < 0) continue; 
        
        // Find largest k such that B[k] <= rem
        int k = upper_bound(B.begin(), B.end(), rem) - B.begin() - 1;
        
        ll val = updates[i].y + k - c;
        if (val >= max_val) {
            max_val = val;
            best_u = i;
        }
    }
    
    if (best_u != -1) {
        if (max_val > dp[q_idx]) dp[q_idx] = max_val;
        solve_queries(updates, queries, q_l, q_mid - 1, u_l, best_u);
        solve_queries(updates, queries, q_mid + 1, q_r, best_u, u_r);
    } else {
        // If no valid u found, budget is too small for any update in range.
        // For left queries (smaller budget), they won't find valid u either.
        // For right queries, they might. We keep the range open starting from u_l.
        solve_queries(updates, queries, q_l, q_mid - 1, u_l, u_l);
        solve_queries(updates, queries, q_mid + 1, q_r, u_l, u_r);
    }
}

// CDQ Divide and Conquer
void cdq(int l, int r) {
    if (l == r) return;
    int mid = (l + r) / 2;
    
    cdq(l, mid);
    
    // Build skyline from left half [l, mid]
    vector<Point> updates;
    for (int i = l; i <= mid; ++i) {
        if (dp[i] <= -INF) continue;
        if (updates.empty()) {
            updates.push_back({S[i], dp[i]});
        } else {
            // Since S[i] is non-decreasing, we are appending to the right
            if (S[i] == updates.back().x) {
                updates.back().y = max(updates.back().y, dp[i]);
            } else {
                // Keep only points with increasing y (Skyline)
                if (dp[i] > updates.back().y) {
                    updates.push_back({S[i], dp[i]});
                }
            }
        }
    }
    
    if (!updates.empty()) {
        vector<int> queries;
        for (int i = mid + 1; i <= r; ++i) {
            queries.push_back(i);
        }
        solve_queries(updates, queries, 0, queries.size() - 1, 0, updates.size() - 1);
    }
    
    cdq(mid + 1, r);
}

void solve() {
    if (!(cin >> n >> m >> c)) return;
    
    a.resize(n);
    S.resize(n + 1);
    S[0] = 0;
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        S[i+1] = S[i] + a[i];
    }
    
    b.resize(m);
    B.resize(m + 1);
    B[0] = 0;
    for (int i = 0; i < m; ++i) {
        cin >> b[i];
        B[i+1] = B[i] + b[i];
    }
    
    dp.assign(n + 1, -INF);
    dp[0] = 0;
    
    cdq(0, n);
    
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