#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>
#include <chrono>
#include <cstdlib>

using namespace std;

int n;
map<pair<int, int>, int> memo;

// Wrapper for interactive query
int query(int i, int j) {
    if (i > j) swap(i, j);
    if (i == j) return -1; // Should not happen in valid logic
    if (memo.count({i, j})) return memo[{i, j}];
    
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return memo[{i, j}] = res;
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int estimate(int u) {
    // Determine how many random samples to take based on remaining budget
    int used = memo.size();
    // We reserve n queries for the final output phase (conservatively)
    int budget_left = 4269 - used - n; 
    
    int K = 18; // Default sample size
    if (budget_left < 100) K = 13;
    if (budget_left < 50) K = 8;
    if (budget_left < 20) K = max(1, budget_left / 2); // Emergency mode
    
    // Cannot sample more than n-1 distinct elements
    if (K > n - 1) K = n - 1;

    int val = -1;
    
    // Pick K distinct random indices
    vector<int> others;
    others.reserve(n);
    for(int i=1; i<=n; ++i) {
        if (i != u) others.push_back(i);
    }
    
    // Partial shuffle to pick K random elements
    for(int i=0; i<K; ++i) {
        int idx = uniform_int_distribution<int>(i, others.size()-1)(rng);
        swap(others[i], others[idx]);
    }
    
    for(int i=0; i<K; ++i) {
        int v = others[i];
        int res = query(u, v);
        if (val == -1) val = res;
        else val &= res;
    }
    // Fallback if K=0 (shouldn't happen given constraints)
    if (val == -1) return (1<<30) - 1; 
    return val;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // We process indices in a random order to ensure probabilistic bounds on swaps
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);

    // Initial candidate for 0
    int curr = p[0];
    int curr_val = estimate(curr);

    // Iterate through the permutation
    for (int i = 1; i < n; ++i) {
        int next_candidate = p[i];
        
        int res = query(curr, next_candidate);
        
        // The result of OR always contains the bits of the current candidate.
        // We can use this to tighten our estimate of curr_val.
        curr_val &= res;
        
        // If the result equals our estimate of curr, it means next_candidate 
        // is a submask of curr (based on current knowledge).
        // Since all elements are distinct, this implies next_candidate < curr (in bitwise sense).
        // This is a candidate for being 0 (or closer to 0).
        if (res == curr_val) {
            curr = next_candidate;
            curr_val = estimate(curr);
        }
    }

    // curr should now be the index of 0.
    // Recover the entire permutation by querying curr with everyone else.
    vector<int> ans(n + 1);
    ans[curr] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == curr) continue;
        ans[i] = query(curr, i);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}