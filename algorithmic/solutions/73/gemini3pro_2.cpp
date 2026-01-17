#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Memoization table for storing query results.
// N <= 2000, so 2005x2005 is sufficient.
int memo[2005][2005];
int n;

// Function to query the interactive system.
// Uses memoization to avoid repeating queries.
// Query format: "0 l r"
int query(int l, int r) {
    if (l >= r) return 0;
    if (memo[l][r] != -1) return memo[l][r];

    cout << "0 " << l << " " << r << endl;
    int res;
    cin >> res;
    return memo[l][r] = res;
}

// Comparator function for sorting indices.
// Returns true if p[i] < p[j].
bool compare_indices(int i, int j) {
    if (i == j) return false;

    int u = i, v = j;
    bool swapped = false;
    // Ensure u < v for the formula
    if (u > v) {
        swap(u, v);
        swapped = true;
    }

    // Determine parity of [p[u] > p[v]]
    // Formula: (Q(u, v) - Q(u, v-1) - Q(u+1, v) + Q(u+1, v-1)) mod 2
    // Since we are in mod 2, subtraction is same as addition (XOR).
    int q1 = query(u, v);
    int q2 = query(u, v - 1);
    int q3 = query(u + 1, v);
    int q4 = query(u + 1, v - 1);

    int is_greater = (q1 ^ q2 ^ q3 ^ q4) & 1;

    if (!swapped) {
        // We want to check if p[u] < p[v].
        // This is true if p[u] > p[v] is false (0).
        return is_greater == 0;
    } else {
        // We want to check if p[v] < p[u].
        // This is equivalent to p[u] > p[v], which is true if is_greater is 1.
        return is_greater == 1;
    }
}

int main() {
    // Read n
    if (!(cin >> n)) return 0;

    // Initialize memo table
    for (int i = 0; i <= n; ++i) {
        for (int j = 0; j <= n; ++j) {
            memo[i][j] = -1;
        }
    }

    // Vector of indices 1 to n
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[i] = i + 1;
    }

    // Sort the indices based on the hidden permutation values
    stable_sort(p.begin(), p.end(), compare_indices);

    // Reconstruct the permutation
    // After sorting, p[k] holds the original index of the (k+1)-th smallest value.
    // Therefore, answer[p[k]] = k + 1.
    vector<int> ans(n + 1);
    for (int k = 0; k < n; ++k) {
        ans[p[k]] = k + 1;
    }

    // Output the final answer in format "1 p1 p2 ... pn"
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}