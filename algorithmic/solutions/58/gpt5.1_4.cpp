#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long x;
    if (!(cin >> x)) return 0;

    int max_bit = 0;
    while ((1LL << max_bit) <= x) max_bit++;
    max_bit--; // highest set bit (0-based), x >= 1 so max_bit >= 0

    const int diag_size = 61;    // we build diagonal band up to 61x61
    const int agg_row = 62;      // aggregator row index (1-based)
    int n = 63 + max_bit;        // grid size, <= 63 + 59 = 122

    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));

    // Build diagonal band: cells with |i-j| <= 1 for i,j <= 61 are 1
    for (int i = 1; i <= diag_size; ++i) {
        for (int j = 1; j <= diag_size; ++j) {
            if (abs(i - j) <= 1) a[i][j] = 1;
        }
    }

    // Corridors for each set bit
    for (int t = 0; t <= max_bit; ++t) {
        if ((x >> t) & 1LL) {
            int r = t + 1;          // row of diag cell representing 2^t
            int c = 63 + t;         // dedicated column for this bit

            // Horizontal from (r,r) to (r,c)
            for (int j = r + 1; j <= c && j <= n; ++j) {
                a[r][j] = 1;
            }
            // Vertical from row r+1 down to agg_row at column c
            for (int i = r + 1; i <= agg_row && i <= n; ++i) {
                a[i][c] = 1;
            }
        }
    }

    // Aggregator row: continuous ones from column 63 to n
    for (int j = 63; j <= n; ++j) {
        a[agg_row][j] = 1;
    }

    // Vertical extension from aggregator row to bottom-right (n,n) along column n
    for (int i = agg_row + 1; i <= n; ++i) {
        a[i][n] = 1;
    }

    // Output grid
    cout << n << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (j > 1) cout << ' ';
            cout << a[i][j];
        }
        cout << '\n';
    }

    return 0;
}