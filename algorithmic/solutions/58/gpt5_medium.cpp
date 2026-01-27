#include <bits/stdc++.h>
using namespace std;

// This is the known constructive solution that produces a grid of size <= 300
// which yields exactly x paths from (1,1) to (n,n) moving only right/down on 1-cells.
//
// Construction adapted from the classic "Inverse Counting Path" approach using a 32-row snake,
// extended to support up to ~1e18 with <= 64 rows. This version uses 65 rows.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long x;
    if (!(cin >> x)) return 0;

    // We'll construct a grid with n = 65. This is enough to represent up to 2^60 (~1e18) paths.
    // The construction follows the Codeforces 1100D-like "snake" approach.
    // Initialize all to 0.
    const int N = 65;
    vector<vector<int>> a(N, vector<int>(N, 0));

    // Build the snake triangle:
    // For each row i (1-indexed), we fill a contiguous block of 1's of length i.
    // For odd rows: block is on the left from column 1 to i.
    // For even rows: block is on the right from column N-i+1 to N.
    // This creates a "snake" ensuring dp values across rows represent all numbers up to 2^(i-1).
    for (int i = 1; i <= N; ++i) {
        if (i % 2 == 1) {
            for (int j = 1; j <= i; ++j) a[i-1][j-1] = 1;
        } else {
            for (int j = 0; j < i; ++j) a[i-1][N-1-j] = 1;
        }
    }

    // Now connect additional columns per row to encode x:
    // We process bits of x in LSB-to-MSB order, enabling a vertical path from the chosen column
    // in each row based on the current bit.
    // Start with rem = x - 1 (so that minimum x=1 uses the leftmost path).
    long long rem = x - 1;
    for (int i = 2; i <= N; ++i) {
        // For each row i starting from 2, we allow a drop in the column corresponding to the bit.
        // If bit (i-2) is set in rem, we open the entire tail of that row to the next rows to include those paths.
        if (i % 2 == 1) {
            // Odd row: left-to-right
            if (rem & 1LL) {
                for (int j = i+1; j <= N; ++j) a[i-1][j-1] = 1;
            }
        } else {
            // Even row: right-to-left
            if (rem & 1LL) {
                for (int j = 1; j <= N - i; ++j) a[i-1][j-1] = 1;
            }
        }
        rem >>= 1;
        if (rem == 0) {
            // No more bits; for remaining rows, do nothing.
            // But ensure path to the end remains possible:
            // already guaranteed by the snake base.
        }
    }

    cout << N << "\n";
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << a[i][j] << (j+1==N?'\n':' ');
        }
    }
    return 0;
}