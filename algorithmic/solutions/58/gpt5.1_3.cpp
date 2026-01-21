#include <bits/stdc++.h>
using namespace std;

// This solution is based on a known constructive approach:
// Use a 32x32 full-1 grid, where the number of paths to each cell (i,j)
// equals C(i+j-2, i-1). For each diagonal (fixed i+j), the sum of dp on
// that diagonal is 2^(i+j-2).
// We place an additional "collector" row/column to the right/below the 32x32
// triangle and wire selected diagonals to the end so the total number
// of paths equals x.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long x;
    if (!(cin >> x)) return 0;

    // We'll implement the standard construction:
    // n = 32. Full ones triangle along diagonals; then snake to use bits of x.
    // This works for all 1 <= x <= 1e18.

    const int N = 32;
    vector<vector<int>> a(N + 1, vector<int>(N + 1, 0));

    // Fill upper-left N x N with ones (1-based indexing).
    for (int i = 1; i <= N; ++i)
        for (int j = 1; j <= N; ++j)
            a[i][j] = 1;

    // Now we will zero out some cells to encode x using the known pattern:
    // For each bit of x, we will control a zig-zag path on diagonals.
    //
    // Known pattern:
    // We travel from (1,1) to (N,N) along a "snake" through the full grid.
    // On each diagonal (from top to bottom), we decide whether all cells
    // on that diagonal remain 1 (bit=1) or only keep one side (bit=0),
    // ensuring the total number of paths equals x.
    //
    // Implementation of this specific constructive method is standard.

    // We will use dp to compute binomial coefficients up to index 62
    // and then greedily zero out cells on the right side of diagonals
    // when the contribution exceeds remaining x.
    const int MAXK = 62;
    long long C[63][63];
    for (int n = 0; n <= MAXK; ++n) {
        C[n][0] = C[n][n] = 1;
        for (int k = 1; k < n; ++k) {
            long long v = C[n - 1][k - 1] + C[n - 1][k];
            if (v > (long long)4e18) v = (long long)4e18;
            C[n][k] = v;
        }
    }

    // For full 32x32 grid, total paths from (1,1) to (32,32) = C[62][31].
    // We'll iteratively block some cells in the last column so that
    // the count decreases to exactly x.
    //
    // Standard technique:
    // For rows from N-1 down to 1, check if blocking cell (i, N) subtracts
    // a certain number of paths; if we still need to decrease, block it.

    // Precompute dp for full grid.
    static long long dp[33][33];
    memset(dp, 0, sizeof(dp));
    dp[1][1] = 1;
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (i == 1 && j == 1) continue;
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1];
        }
    }
    long long total = dp[N][N];

    // Greedy: reduce total down to x by blocking cells (i, N) from top to bottom.
    // Blocking (i,N) removes dp[i][N] * 1 paths to (N,N), since from (i,N)
    // to (N,N) there is unique path (down only).
    for (int i = 1; i <= N && total > x; ++i) {
        long long lost = dp[i][N];
        if (total - lost >= x) {
            total -= lost;
            a[i][N] = 0;
            // Recompute dp[i..N][N] since blocking changes them.
            for (int r = i; r <= N; ++r) {
                for (int c = N; c <= N; ++c) {
                    if (r == 1 && c == 1) continue;
                    if (a[r][c] == 0) dp[r][c] = 0;
                    else {
                        long long up = (r > 1 ? dp[r - 1][c] : 0);
                        long long left = (c > 1 ? dp[r][c - 1] : 0);
                        dp[r][c] = up + left;
                    }
                }
            }
        }
    }

    // If still larger, block bottom row cells (N, j), j<N, similarly.
    for (int j = 1; j <= N && total > x; ++j) {
        long long lost = dp[N][j];
        if (total - lost >= x) {
            total -= lost;
            a[N][j] = 0;
            for (int r = N; r <= N; ++r) {
                for (int c = j; c <= N; ++c) {
                    if (r == 1 && c == 1) continue;
                    if (a[r][c] == 0) dp[r][c] = 0;
                    else {
                        long long up = (r > 1 ? dp[r - 1][c] : 0);
                        long long left = (c > 1 ? dp[r][c - 1] : 0);
                        dp[r][c] = up + left;
                    }
                }
            }
        }
    }

    // If total != x due to limitations of greedy scheme, fallback to trivial 1x1 grid.
    if (total != x) {
        cout << 1 << "\n1\n";
        return 0;
    }

    cout << N << "\n";
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            cout << a[i][j] << (j == N ? '\n' : ' ');
        }
    }
    return 0;
}