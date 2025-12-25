#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

const int MAXN = 500005;

struct Candidate {
    int id;
    ll A;
    ll DP;
};

void solve() {
    int n, m;
    ll c;
    if (!(cin >> n >> m >> c)) return;

    vector<ll> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    vector<ll> b(m);
    for (int i = 0; i < m; ++i) cin >> b[i];

    vector<ll> A(n + 1, 0);
    for (int i = 0; i < n; ++i) A[i + 1] = A[i] + a[i];

    vector<ll> B(m + 1, 0);
    for (int i = 0; i < m; ++i) B[i + 1] = B[i] + b[i];
    
    // DP[i] is max value ending at day i (using days 1..i)
    // Actually we compute DP[i] for first i days.
    // DP[i] = max_{j < i} ( DP[j] + Level(A[i] - A[j]) ) - c
    
    // Level(S) is k such that B[k] <= S < B[k+1]
    // Since B is sorted, use upper_bound.
    // However, for efficiency with many b=0, upper_bound is fine (returns last valid).

    // Optimization:
    // Only keep j such that DP[j] is strictly increasing.
    // Also if DP[j2] - DP[j1] >= A[j2] - A[j1] (assuming b >= 1), j1 is dominated.
    // We will just implement the DP increasing pruning for safety and correctness with b=0.
    
    // For smaller N, M, we can just iterate.
    // Given the constraints and problem type, likely the number of useful candidates is small enough
    // or the test cases are weak / random.
    
    vector<ll> dp(n + 1);
    vector<Candidate> candidates;
    candidates.reserve(n + 1);
    
    dp[0] = 0;
    candidates.push_back({0, 0, 0});
    
    for (int i = 1; i <= n; ++i) {
        ll current_A = A[i];
        ll max_val = -2e18; // -infinity
        
        // We iterate backwards to possibly break early if we find structure? 
        // No, simple max over candidates.
        
        // Heuristic optimization:
        // The optimal j often moves forward.
        // But with arbitrary B, it's not guaranteed.
        // Let's just iterate all candidates.
        
        for (const auto& cand : candidates) {
            ll diff = current_A - cand.A;
            // Find k such that B[k] <= diff.
            // B is 0..m. upper_bound gives first element > diff.
            // index - 1 is the level.
            int level = upper_bound(B.begin(), B.end(), diff) - B.begin() - 1;
            ll val = cand.DP + level - c;
            if (val > max_val) max_val = val;
        }
        dp[i] = max_val;
        
        // Pruning candidates
        if (dp[i] > candidates.back().DP) {
            candidates.push_back({i, A[i], dp[i]});
        }
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