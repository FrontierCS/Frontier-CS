#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    if (!(cin >> x)) return 0;

    const int K = 60;                 // enough for x <= 1e18 < 2^60
    const int n = 2 * K + 4;          // 124, with a buffer below the chain

    vector<vector<int>> a(n, vector<int>(n, 0));

    // Build doubling chain
    for (int i = 0; i < K; i++) {
        int r = 2 * i;
        int c = 2 * i;

        // 2x2 square
        a[r][c] = 1;       // A = u_i
        a[r][c + 1] = 1;   // B
        a[r + 1][c] = 1;   // C
        a[r + 1][c + 1] = 1; // D

        // Bridge to next u_{i+1} at (r+2, c+2)
        a[r + 1][c + 2] = 1; // E
        a[r + 2][c + 2] = 1; // u_{i+1}
    }

    // Add exits according to bits of x
    for (int i = 0; i < K; i++) {
        if ((x >> i) & 1ULL) {
            int col = 2 * i;
            int startRow = 2 * i + 2; // F_i
            for (int r = startRow; r < n; r++) a[r][col] = 1;
        }
    }

    // Bottom collector row to reach (n,n)
    for (int j = 0; j < n; j++) a[n - 1][j] = 1;

    cout << n << "\n";
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (j) cout << ' ';
            cout << a[i][j];
        }
        cout << "\n";
    }

    return 0;
}