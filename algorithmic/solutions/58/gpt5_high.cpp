#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if (!(cin >> x)) return 0;

    if (x == 1ULL) {
        cout << 1 << "\n";
        cout << 1 << "\n";
        return 0;
    }

    int K = 0;
    while ((1ULL << (K + 1)) <= x) ++K;

    int n = 2 * K + 2;
    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));

    // Top row ones to enable unique horizontal movement
    for (int j = 1; j <= n; ++j) a[1][j] = 1;

    // Unique corridor from (1,1) to (3,3) avoiding (2,3)
    a[2][2] = 1;
    a[3][2] = 1;
    a[3][3] = 1;

    // Build K doubling blocks with spacing 2
    for (int i = 0; i < K; ++i) {
        int r = 3 + 2 * i;
        a[r][r] = 1;
        a[r][r + 1] = 1;
        a[r + 1][r] = 1;
        a[r + 1][r + 1] = 1;
    }

    // Bridge between consecutive blocks (down then right)
    for (int i = 0; i < K - 1; ++i) {
        int r = 3 + 2 * i;
        a[r + 2][r + 1] = 1;
    }

    // Set (2,3) to 0 explicitly to avoid unwanted path (may already be 0)
    // Not strictly necessary since initialized to 0, kept here for clarity.
    // a[2][3] = 0;

    // Add injections according to bits of y = x - 2^K
    unsigned long long y = x - (1ULL << K);
    for (int t = 0; t < K; ++t) {
        if ((y >> (K - 1 - t)) & 1ULL) {
            int col = 4 + 2 * t;
            for (int row = 1; row <= col; ++row) a[row][col] = 1;
        }
    }

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