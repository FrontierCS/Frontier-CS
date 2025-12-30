#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>

using namespace std;

// The problem asks us to find a hidden permutation p of size n.
// We can make queries to find the parity of the number of inversions in a subarray p[l...r].
// We have a budget of 1,999,000 queries for N <= 2000.
// We can determine the relative order of any pair (p[i], p[j]) using 4 queries (or fewer if cached).
// By using these comparisons in a sorting algorithm (Merge Sort via stable_sort), 
// we can sort the indices based on the values of p, thus reconstructing p.
// The number of comparisons for sorting is O(N log N).
// Each comparison takes constant number of queries.
// Total queries will be roughly 4 * N * log2(N) which is approximately 88,000 for N=2000,
// well within the limit.

const int MAXN = 2005;
// Memoization table to store query results. -1 indicates not computed.
int memo[MAXN][MAXN];

// Function to query the interactor.
// Uses 1-based indexing as per problem description.
// Query format: "? l r" based on the Example.
int ask(int l, int r) {
    if (l >= r) return 0; // Subarray of length 0 or 1 has 0 inversions
    if (memo[l][r] != -1) return memo[l][r];
    
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return memo[l][r] = res;
}

// Custom comparator for sorting indices.
// Returns true if p[i] < p[j].
bool compare(int i, int j) {
    if (i == j) return false;
    
    int u = i;
    int v = j;
    bool swapped = false;
    
    // Ensure u < v for range queries
    if (u > v) {
        swap(u, v);
        swapped = true;
    }
    
    // We want to find if p[u] > p[v]. Let x_{u, v} = 1 if p[u] > p[v], else 0.
    // The parity of inversions in p[u...v], denoted Q(u, v), is related to x_{u, v} by:
    // Q(u, v) = x_{u, v} + Q(u+1, v) + Q(u, v-1) - Q(u+1, v-1)  (mod 2)
    // Thus, x_{u, v} = Q(u, v) XOR Q(u+1, v) XOR Q(u, v-1) XOR Q(u+1, v-1)
    
    int val = ask(u, v) ^ ask(u + 1, v) ^ ask(u, v - 1) ^ ask(u + 1, v - 1);
    
    // val is 1 if p[u] > p[v], 0 otherwise.
    
    if (!swapped) {
        // We wanted to check p[i] < p[j], i.e., p[u] < p[v].
        // This is true if p[u] > p[v] is false (val == 0).
        return val == 0;
    } else {
        // We wanted to check p[i] < p[j], i.e., p[v] < p[u].
        // This is true if p[u] > p[v] is true (val == 1).
        return val == 1;
    }
}

int main() {
    // Sync off for performance, though not strictly critical for interactive with endl
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Initialize memo table
    memset(memo, -1, sizeof(memo));

    // Initialize indices p[0...n-1] with 1...n
    vector<int> p(n);
    for(int i = 0; i < n; ++i) {
        p[i] = i + 1;
    }

    // Sort the indices based on the values in the hidden permutation.
    // stable_sort typically uses Merge Sort, which is efficient and comparison-based.
    stable_sort(p.begin(), p.end(), compare);

    // Reconstruct the permutation from sorted indices.
    // p[k] holds the original index of the (k+1)-th smallest element.
    // So if p[k] = idx, then hidden_permutation[idx] = k + 1.
    vector<int> ans(n + 1);
    for(int i = 0; i < n; ++i) {
        ans[p[i]] = i + 1;
    }

    // Output the result
    cout << "!";
    for(int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}