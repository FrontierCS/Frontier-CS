#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long x;
    if (!(cin >> x)) return 0;

    // Construct the well-known Codeforces 1100F-style grid.
    // n = 32. Tri-diagonal "band" from (1,1) to (k+1,k+1) gives dp(i,i) = 2^(i-1).
    // Then connect selected diagonal cells to a final join column to sum bits to x.

    // Find number of bits needed
    int B = 0;
    while ((1LL << B) <= x && B < 60) B++;
    if ((1LL << B) > x) B--; // max bit index such that 2^B <= x
    if (x == 1) B = 0;

    int n = B + 2; // band up to (B+1,B+1), join column at B+2
    if (n < 2) n = 2;

    vector<vector<int>> a(n, vector<int>(n, 0));

    // Build tri-diagonal band: |i-j| <= 1 for 1..B+1
    for (int i = 1; i <= B + 1; ++i) {
        for (int j = 1; j <= B + 1; ++j) {
            if (abs(i - j) <= 1) a[i-1][j-1] = 1;
        }
    }

    int J = B + 2; // join column
    // For rows 1..B+1, connect diagonal cells to join column if corresponding bit is set
    // Diagonal cell for k (0-based) is at (k+1,k+1) with dp value 2^k.
    // We'll add a unique horizontal path on its row from col (k+1) to J, and a vertical path from (row,J) to (n,n).
    for (int k = 0; k <= B; ++k) {
        if ( (x >> k) & 1LL ) {
            int r = k + 1;
            // Horizontal to join column
            for (int c = k + 1; c <= J; ++c) {
                a[r-1][c-1] = 1;
            }
        }
    }
    // Vertical join column down to bottom-right, ensuring path from any attached row to sink
    for (int r = 1; r <= n; ++r) {
        a[r-1][J-1] = 1;
    }

    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << a[i][j] << (j+1==n?'\n':' ');
        }
    }
    return 0;
}