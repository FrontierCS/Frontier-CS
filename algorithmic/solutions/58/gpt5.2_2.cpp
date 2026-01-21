#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    if (!(cin >> x)) return 0;

    int B = 64 - __builtin_clzll(x); // bit length, x >= 1
    if (B == 1) {
        cout << 1 << "\n";
        cout << 1 << "\n";
        return 0;
    }

    int n = 2 * B;
    vector<vector<int>> a(n, vector<int>(n, 0));

    // Open accumulator column (last column)
    for (int r = 0; r < n; r++) a[r][n - 1] = 1;

    // Power-of-two generator (stretched diagonal diamonds)
    a[0][0] = 1; // P0
    for (int i = 0; i <= B - 2; i++) {
        int r = 2 * i;
        int c = i;
        a[r][c] = 1;         // P_i
        a[r][c + 1] = 1;     // top-right
        a[r + 1][c] = 1;     // bottom-left
        a[r + 1][c + 1] = 1; // bottom-right (doubles)
        a[r + 2][c + 1] = 1; // P_{i+1}
    }

    // Add selected powers into accumulator column using horizontal corridors on rows 2*i
    for (int i = 0; i < B; i++) {
        if ((x >> i) & 1ULL) {
            int r = 2 * i;
            for (int c = i; c <= n - 2; c++) a[r][c] = 1;
        }
    }

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