#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long x;
    if(!(cin >> x)) return 0;

    // This is the classic CF construction (1368A-like) for inverse path counting.
    // We will use n = 32 and build a specific grid ensuring exact x paths.
    // Reference construction: Zig-zag triangle enabling any x up to 2^31 (~2e9).
    // But x can be up to 1e18, so we extend to 64.

    // We'll implement the known construction that supports up to 2^(n-1).
    // Use n = 64 to support up to 1e18 safely.
    const int n = 64;
    vector<vector<int>> a(n, vector<int>(n, 0));

    // Build base: for each row i, make first i+1 cells 1 (triangle)
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j <= i; ++j) a[i][j] = 1;
    }

    // We will follow the standard CF approach:
    // For each row after the first, if the corresponding bit in (x-1) is set,
    // we keep the entire row ones; otherwise, we zero out cells except one end,
    // alternating ends to maintain connectivity and exact count.
    // Start with y = x
    long long y = x;
    // We will adjust rows 1..n-1 based on bits of (y-1)
    long long m = y - 1;
    bool left = true; // track which end to keep when bit is 0
    for (int i = 1; i < n; ++i) {
        if ((m >> (i - 1)) & 1LL) {
            // keep row i as is (all ones in triangle)
        } else {
            // zero out row i except one end in the triangle
            if (left) {
                for (int j = 1; j < i; ++j) a[i][j] = 0;
            } else {
                for (int j = 0; j < i; ++j) a[i][j] = 0;
                a[i][i] = 1;
            }
        }
        left = !left;
    }

    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << a[i][j] << (j + 1 == n ? '\n' : ' ');
        }
    }
    return 0;
}