#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long x;
    if (!(cin >> x)) return 0;

    if (x == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }

    int L = 64 - __builtin_clzll(x); // number of bits
    vector<int> bits;
    bits.reserve(L);
    for (int i = L - 1; i >= 0; --i) bits.push_back((x >> i) & 1ULL);

    int row_last = 1 + 2 * (L - 1);
    int col_last = 1 + 3 * (L - 1);
    int n = max(row_last, col_last) + 1;
    if (n > 300) n = 300; // should never happen for given constraints

    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));

    // Top row to reach injection columns
    for (int j = 1; j <= col_last; ++j) a[1][j] = 1;

    // Build pipeline
    for (int i = 0; i <= L - 2; ++i) {
        int r = 1 + 2 * i;
        int c = 1 + 3 * i;

        a[r][c] = 1;         // S_i
        a[r][c + 1] = 1;     // B
        a[r + 1][c] = 1;     // C
        a[r + 1][c + 1] = 1; // D (double)

        a[r + 2][c + 1] = 1; // wire down
        a[r + 2][c + 2] = 1; // wire right (W)
        a[r + 2][c + 3] = 1; // S_{i+1}

        if (bits[i + 1] == 1) {
            int col = c + 3;     // injection column
            int inj_row = r + 1; // injection cell row
            for (int rr = 1; rr <= inj_row; ++rr) a[rr][col] = 1;
        }
    }

    // Connect last stage to (n,n) uniquely: right to last column, then down
    for (int j = col_last; j <= n; ++j) a[row_last][j] = 1;
    for (int i = row_last; i <= n; ++i) a[i][n] = 1;

    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << a[i][j] << (j == n ? '\n' : ' ');
        }
    }
    return 0;
}