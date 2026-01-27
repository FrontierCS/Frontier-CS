#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <cstdlib>

using namespace std;

// Global random engine
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int n;

// Function to perform a query
int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Function to estimate the value of p[idx] by querying against random indices.
// With 13 queries, the probability of bit error is negligible (approx N * 0.5^13).
int get_val(int idx) {
    int val = -1;
    for (int k = 0; k < 13; ++k) {
        int r = (rng() % n) + 1;
        while (r == idx) {
            r = (rng() % n) + 1;
        }
        int res = ask(idx, r);
        if (val == -1) val = res;
        else val &= res;
    }
    return val;
}

void solve() {
    if (!(cin >> n)) return;

    // Create a list of indices 1 to n
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    // Shuffle to process in random order
    shuffle(p.begin(), p.end(), rng);

    // Initialize current candidate for 0
    int best = p[0];
    int current_val = get_val(best);

    // Memoization table to store results of queries against the CURRENT best
    // This helps save queries in the final reconstruction phase
    vector<int> memo(n + 1, -1);

    // Linear scan to find the element 0
    for (int i = 1; i < n; ++i) {
        int u = p[i];
        
        // Query current best against candidate u
        int res = ask(best, u);

        // Check if p[u] is a candidate to be a submask of current best (i.e., smaller or equal)
        // Since permutation elements are unique, this implies strictly smaller (subset)
        if (res == current_val) {
            best = u;
            current_val = get_val(best);
            
            // Invalidate memoized results as they were against the old best
            // We use simple fill because number of updates is small (bounded by bit depth ~11)
            fill(memo.begin(), memo.end(), -1);
        } else {
            // Save result to avoid requerying later
            memo[u] = res;
        }
    }

    // Now 'best' should be the index where p[best] == 0.
    // Reconstruct the whole permutation.
    vector<int> ans(n);
    ans[best - 1] = 0;
    
    for (int i = 1; i <= n; ++i) {
        if (i == best) continue;
        
        // If we have a valid memoized result, use it. Otherwise query.
        // Since p[best] is 0, (p[best] | p[i]) == p[i].
        if (memo[i] != -1) {
            ans[i - 1] = memo[i];
        } else {
            ans[i - 1] = ask(best, i);
        }
    }

    // Output answer
    cout << "!";
    for (int x : ans) {
        cout << " " << x;
    }
    cout << endl;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}