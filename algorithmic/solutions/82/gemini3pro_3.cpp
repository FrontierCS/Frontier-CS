#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <numeric>
#include <random>
#include <chrono>

using namespace std;

// Global variables to store n and the query cache
int n;
map<pair<int, int>, int> memo;

// Function to perform a query or retrieve from cache
int query(int i, int j) {
    if (i > j) swap(i, j);
    if (memo.count({i, j})) return memo[{i, j}];
    
    cout << "? " << i + 1 << " " << j + 1 << endl;
    int res; 
    cin >> res;
    if (res == -1) exit(0); // Terminate on invalid query or limit exceeded
    
    return memo[{i, j}] = res;
}

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Function to estimate the value of p[idx] by querying with random others
// Returns the bitwise AND of ~30 queries, which converges to p[idx]
int get_val(int idx) {
    vector<int> others;
    others.reserve(n - 1);
    for (int i = 0; i < n; ++i) {
        if (i != idx) others.push_back(i);
    }
    // Shuffle to pick random neighbors
    shuffle(others.begin(), others.end(), rng);
    
    int k = min((int)others.size(), 30);
    int val = -1; // Represents all 1s initially
    
    for (int i = 0; i < k; ++i) {
        int res = query(idx, others[i]);
        if (val == -1) val = res;
        else val &= res;
        
        // If val becomes 0, p[idx] must be 0.
        // We can stop early to save queries.
        if (val == 0) return 0;
    }
    return val;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n)) return 0;

    // Create a random permutation of indices to iterate through
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);
    shuffle(p.begin(), p.end(), rng);

    // Initial candidate for the index of 0
    int cand = p[0];
    int cand_val = get_val(cand);

    // Iterate through other indices to see if we find a "smaller" element (submask)
    for (int i = 1; i < n; ++i) {
        if (cand_val == 0) break; // We found 0
        
        int u = p[i];
        // Query current candidate against new element
        int res = query(cand, u);
        
        // If result equals cand_val, it means p[u] is a submask of p[cand]
        // Since all elements are distinct, p[u] is strictly "smaller" (or we just found a submask)
        if (res == cand_val) {
            cand = u;
            cand_val = get_val(cand);
        }
    }

    // Now 'cand' should be the index of 0.
    // We can find all other elements by querying them against 'cand'.
    vector<int> ans(n);
    ans[cand] = 0;
    for (int i = 0; i < n; ++i) {
        if (i == cand) continue;
        // p[cand] is 0, so p[cand] | p[i] = 0 | p[i] = p[i]
        ans[i] = query(cand, i);
    }

    // Output the result
    cout << "!";
    for (int i = 0; i < n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}