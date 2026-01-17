#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

// Global variables to store cache and N
// cache_q stores the result of queries Q(l, r)
// Initialized to -1 to indicate not computed
int n;
int cache_q[2005][2005];

// Function to perform query or retrieve from cache
// Returns parity of inversions in p[l...r]
int ask(int l, int r) {
    if (l >= r) return 0; // Base case: range length < 2 implies 0 inversions
    if (cache_q[l][r] != -1) return cache_q[l][r];
    
    // Output query in specified format: 0 l r
    cout << "0 " << l << " " << r << endl;
    
    int res;
    cin >> res;
    return cache_q[l][r] = res;
}

// Helper to safely get query results handling boundary conditions
int get_Q(int l, int r) {
    if (l >= r) return 0;
    return ask(l, r);
}

// Comparator for sorting indices based on the hidden permutation values
// Returns true if hidden_p[idx1] < hidden_p[idx2]
bool compare_indices(int idx1, int idx2) {
    if (idx1 == idx2) return false;
    
    int u = idx1;
    int v = idx2;
    bool swapped = false;
    
    // Ensure u < v for range queries
    if (u > v) {
        swap(u, v);
        swapped = true;
    }
    
    // We determine if p[u] > p[v] (where u < v)
    // The relationship is derived from inclusion-exclusion on inversion counts:
    // [p[u] > p[v]] = Q(u, v) - Q(u+1, v) - Q(u, v-1) + Q(u+1, v-1)
    // Working modulo 2 (XOR):
    int q1 = get_Q(u, v);
    int q2 = get_Q(u + 1, v);
    int q3 = get_Q(u, v - 1);
    int q4 = get_Q(u + 1, v - 1);
    
    int is_greater = q1 ^ q2 ^ q3 ^ q4;
    
    // is_greater == 1 implies p[u] > p[v]
    
    if (!swapped) {
        // We want to return true if p[idx1] < p[idx2] => p[u] < p[v]
        return is_greater == 0;
    } else {
        // We want to return true if p[idx1] < p[idx2] => p[v] < p[u]
        // p[v] < p[u] is equivalent to p[u] > p[v]
        return is_greater == 1;
    }
}

int main() {
    // Read n
    if (!(cin >> n)) return 0;
    
    // Initialize cache
    for (int i = 0; i <= n; ++i) {
        for (int j = 0; j <= n; ++j) {
            cache_q[i][j] = -1;
        }
    }
    
    // Initialize indices p = {1, 2, ..., n}
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    // Sort the indices based on the values in the hidden permutation
    // stable_sort uses O(N log N) comparisons, minimizing queries
    stable_sort(p.begin(), p.end(), compare_indices);
    
    // Reconstruct the permutation
    // p[0] is the index of the element with value 1
    // p[1] is the index of the element with value 2, etc.
    vector<int> ans(n + 1);
    for (int i = 0; i < n; ++i) {
        ans[p[i]] = i + 1;
    }
    
    // Output the result in specified format: 1 p1 p2 ... pn
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    
    return 0;
}