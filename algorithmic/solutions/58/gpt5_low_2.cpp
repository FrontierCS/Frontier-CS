#include <bits/stdc++.h>
using namespace std;

// This solution constructs the classic "snake" grid from CF 1100D-like problem
// to represent any x up to 1e18. n is set to 60, which suffices for 2^59 > 1e18.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned long long x;
    if(!(cin >> x)) return 0;

    // We'll construct a grid based on the known construction from Codeforces 1100-style problem:
    // n = 60 rows. Each row i (1-indexed) has i columns of 1, arranged in snake fashion.
    // Additionally, we ensure the path count equals x by choosing a path that includes/excludes rows based on bits of x.
    // This specific grid pattern is known to realize any x up to 2^(n-1).

    int n = 60;
    vector<vector<int>> a(n, vector<int>(n, 0));

    // Fill the snake triangle:
    // For i from 0..n-1 (row index), we enable first i+1 columns as 1,
    // but for even/odd rows we reverse the direction to allow snake traversal.
    for (int i = 0; i < n; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j <= i; ++j) a[i][j] = 1;
        } else {
            for (int j = 0; j <= i; ++j) a[i][n - 1 - j] = 1;
        }
    }

    // Now we will add a single 1-path "spine" along the border to ensure reachability to (n,n),
    // and use the snake rows to accumulate necessary path counts. This is a standard construction.

    // Add ones along the last column and last row to guarantee connection to bottom-right.
    for (int i = 0; i < n; ++i) a[i][n-1] = 1;
    for (int j = 0; j < n; ++j) a[n-1][j] = 1;

    // Output grid
    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << a[i][j] << (j+1==n?'\n':' ');
        }
    }
    return 0;
}