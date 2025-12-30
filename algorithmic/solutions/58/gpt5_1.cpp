#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if (!(cin >> x)) return 0;
    
    // Number of bits
    int M = 0;
    {
        unsigned long long t = x;
        while (t) { ++M; t >>= 1; }
    }
    if (M == 0) {
        // x >= 1 as per constraints, but just in case
        cout << 1 << "\n1\n";
        return 0;
    }
    
    // s0 offset for the chain to avoid interference
    int s0 = 2;
    int n = 2 * M + 3;
    
    vector<vector<int>> a(n, vector<int>(n, 0)); // 0-based indexing
    
    auto set1 = [&](int r, int c) {
        if (r >= 1 && r <= n && c >= 1 && c <= n) a[r-1][c-1] = 1;
    };
    
    // Start cell
    set1(1, 1);
    // Walkway row r=2 across all columns
    for (int j = 1; j <= n; ++j) set1(2, j);
    
    // Bits from MSB to LSB
    vector<int> b(M);
    for (int i = 0; i < M; ++i) {
        b[i] = ( (x >> (M - 1 - i)) & 1ULL ) ? 1 : 0;
    }
    
    for (int p = 0; p < M; ++p) {
        int t = s0 + p;
        // Diamond cells
        set1(2*t, 2*t);
        set1(2*t, 2*t + 1);
        set1(2*t + 1, 2*t);
        set1(2*t + 1, 2*t + 1);
        // Connector from previous step
        if (p > 0) {
            set1(2*t, 2*t - 1); // from D(prev) down to here then right to A
        }
        // Injection column if bit is 1 (from walkway row 2 down to above B)
        if (b[p]) {
            int col = 2*t + 1;
            for (int r = 2; r <= 2*t - 1; ++r) set1(r, col);
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