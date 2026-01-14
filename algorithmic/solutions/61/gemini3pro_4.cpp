#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to find the largest k such that B[k] <= val
// B[k] is the prefix sum of b_1...b_k.
// B[0] = 0.
// We want max k such that B[k] <= val.
int get_level(long long val, const vector<long long>& B) {
    if (val < 0) return -1;
    // B is sorted.
    auto it = upper_bound(B.begin(), B.end(), val);
    return (int)(it - B.begin()) - 1;
}

void solve() {
    int n, m;
    long long c;
    if (!(cin >> n >> m >> c)) return;

    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<long long> b(m);
    for (int i = 0; i < m; ++i) cin >> b[i];

    // Prefix sums for a
    vector<long long> Sa(n + 1, 0);
    for (int i = 0; i < n; ++i) Sa[i + 1] = Sa[i] + a[i];

    // Prefix sums for b. B[k] is requirement for level k.
    vector<long long> B(m + 1, 0);
    for (int i = 0; i < m; ++i) B[i + 1] = B[i] + b[i];

    // Candidates: pairs of (Sa[j], dp[j])
    // We store candidates where dp[j] is a new prefix maximum.
    struct Candidate {
        long long s;
        long long v;
    };
    vector<Candidate> candidates;
    
    // Base case: previous character ended at day 0 (index 0).
    // Sa[0] = 0. dp[0] = 0.
    candidates.push_back({0, 0});
    
    long long current_dp = 0; 
    long long max_dp = 0; // Tracks the maximum dp value seen so far

    for (int i = 1; i <= n; ++i) {
        // We want to calculate dp[i] = max_{j < i} (dp[j] + level(Sa[i] - Sa[j])) - c
        // We iterate over our stored candidates.
        
        long long best_val = -4e18; // Initialize with a very small number
        
        // Optimization: Iterate backwards from the best candidate.
        // We can stop if candidate's potential max value cannot beat current best.
        // Max level is m. So max contribution is v + m - c.
        // If v + m - c <= best_val, this candidate and any previous (smaller v) cannot be optimal.
        
        for (int k = candidates.size() - 1; k >= 0; --k) {
            long long v = candidates[k].v;
            // Pruning condition
            if (v + m - c <= best_val) break;
            
            long long diff = Sa[i] - candidates[k].s;
            long long level = get_level(diff, B);
            long long val = v + level - c;
            
            if (val > best_val) {
                best_val = val;
            }
        }
        
        current_dp = best_val;
        
        // If we found a new max dp, add it to candidates
        if (current_dp > max_dp) {
            max_dp = current_dp;
            candidates.push_back({Sa[i], current_dp});
        }
    }
    
    cout << current_dp << "\n";
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