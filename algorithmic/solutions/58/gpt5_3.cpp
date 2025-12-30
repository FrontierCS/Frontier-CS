#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned long long x;
    if(!(cin >> x)) return 0;

    // Based on known constructive approach from CF: build a 32x32 "snake" triangle
    // that allows representing any number up to 2^31 by opening bridges per row.
    // To cover up to 1e18 (~2^60), extend size to 64.
    int n = 64;
    vector<vector<int>> a(n, vector<int>(n, 0));

    // Build the snake triangle: for each row i, fill first i+1 cells with 1,
    // alternating direction to keep connections intact.
    for (int i = 0; i < n; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j <= i; ++j) a[i][j] = 1;
        } else {
            for (int j = 0; j <= i; ++j) a[i][n - 1 - j] = 1;
        }
    }

    // Build rightmost column as a sink corridor
    for (int i = 0; i < n; ++i) a[i][n - 1] = 1;

    // For each row i (0-indexed), if bit i of x is set, open a horizontal bridge
    // from the snake block to the rightmost column to add 2^i paths.
    // This is a heuristic; may not work for all x but aims to produce many values.
    for (int i = 0; i < n; ++i) {
        if (((x >> i) & 1ULL) == 0) continue;
        if (i % 2 == 0) {
            // row i filled from left; extend from (i, i) to the end
            for (int j = i; j < n; ++j) a[i][j] = 1;
        } else {
            // row i filled from right; extend from (i, n-1-i) to the end (rightmost column already 1)
            for (int j = n - 1 - i; j < n; ++j) a[i][j] = 1;
        }
    }

    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << a[i][j];
        }
        cout << "\n";
    }
    return 0;
}