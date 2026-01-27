#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if (!(cin >> x)) return 0;

    const int K = 60;                  // support up to 2^60 > 1e18
    const int band = K + 1;            // size of doubling band
    const int Xbase = K + 2;           // first column to the right of the band
    const int R0 = K + 10;             // base row for accumulator stages
    const int C = Xbase + K + 2;       // accumulator column, to the right of all vertical wires

    auto r_t = [&](int t){ return R0 + 2 * t; }; // spaced rows to avoid interference
    int last_row = r_t(K);
    int n = max(last_row, C);
    n = max(n, band + 5);

    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));

    // Build the 2x2 doubling chain along the diagonal to create powers of two.
    // After t steps (t from 1..K), cell (t+1, t+1) holds value 2^t.
    for (int t = 1; t <= K; ++t) {
        a[t][t] = 1;
        a[t][t + 1] = 1;
        a[t + 1][t] = 1;
        a[t + 1][t + 1] = 1;
    }
    // Ensure starting cell (1,1) is 1 (already set by t=1, but set explicitly for safety).
    a[1][1] = 1;

    // Set accumulator column C from its start row down to bottom.
    int r_start = r_t(0);
    for (int r = r_start; r <= n; ++r) a[r][C] = 1;

    // For each bit t in x, wire 2^t from its source to the accumulator column.
    for (int t = 0; t <= K; ++t) {
        if (((x >> t) & 1ULL) == 0ULL) continue;

        int rs = (t == 0 ? 1 : t + 1);  // source row
        int cs = (t == 0 ? 1 : t + 1);  // source col
        int Xt = Xbase + t;             // dedicated vertical column for this bit
        int rt = r_t(t);                // stage row for this bit

        // Route right from source to column Xt.
        for (int j = cs + 1; j <= Xt; ++j) a[rs][j] = 1;

        // Route down along column Xt to row rt.
        for (int i = rs + 1; i <= rt; ++i) a[i][Xt] = 1;

        // Route right from Xt to C-1 on row rt (so left neighbor of (rt,C) carries 2^t).
        for (int j = Xt + 1; j <= C - 1; ++j) a[rt][j] = 1;
        // Cell (rt, C) already set to 1 in accumulator column setup.
    }

    // From (n, C) propagate right to (n, n) to place the final result at bottom-right.
    for (int j = C; j <= n; ++j) a[n][j] = 1;

    // Output
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (j > 1) cout << ' ';
            cout << a[i][j];
        }
        cout << "\n";
    }
    return 0;
}