#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if(!(cin >> x)) return 0;

    const int K = 60;            // enough for up to 2^60 > 1e18
    const int R = K + 1;         // bottom row of the diamond chain
    const int M = R + 2;         // merge column for exits (ensure gap from chain)
    const int n = M + 1;         // final grid size (bottom-right at (n,n))

    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0)); // 1-based

    // Build the diamond chain from (1,1) to (R,R)
    int r = 1, c = 1;
    a[r][c] = 1;
    for (int t = 1; t <= K; ++t) {
        a[r][c+1] = 1;
        a[r+1][c] = 1;
        a[r+1][c+1] = 1;
        r++; c++;
    }

    // Build exits for each set bit i: from v_i at (1+i,1+i) to the merge column M, then down to R
    for (int i = 0; i <= K; ++i) {
        if ((x >> i) & 1ULL) {
            int rr = 1 + i;
            int cc = 1 + i;
            // Horizontal from (rr, cc+2) to M (cc+1 is part of the diamond)
            for (int j = cc + 2; j <= M; ++j) a[rr][j] = 1;
            // Vertical from rr..R at column M
            for (int k = rr; k <= R; ++k) a[k][M] = 1;
        }
    }

    // Shared tail from (R, M) -> right to n, then down to n (unique path)
    for (int j = M + 1; j <= n; ++j) a[R][j] = 1;
    for (int i = R; i <= n; ++i) a[i][n] = 1;

    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << a[i][j] << (j == n ? '\n' : ' ');
        }
    }
    return 0;
}