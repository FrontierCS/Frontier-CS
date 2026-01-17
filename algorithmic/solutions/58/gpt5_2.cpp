#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long x;
    if (!(cin >> x)) return 0;

    // Number of bits needed to represent x
    int k = 0;
    unsigned long long t = x;
    while (t > 0) { k++; t >>= 1; }
    if (k == 0) k = 1; // though x >= 1 by constraints

    // Positions of S_i: (r_i, c_i) = (2*i+1, i+1)
    int c_end = k;            // c of S_{k-1}
    int r_max = 2 * k - 1;    // r of S_{k-1}

    int B = c_end + 2;        // barrier column (left of vertical line)
    int V = B + 1;            // vertical line column
    int N = max(V, r_max + 1); // grid size (ensure bottom row after left area)

    vector<vector<int>> a(N + 1, vector<int>(N + 1, 0)); // 1-based

    // Build left area: sequence of (2x2) diamonds (doubling) + vertical padding steps
    int r = 1, c = 1;
    a[r][c] = 1; // S0
    for (int i = 0; i <= k - 2; ++i) {
        a[r][c] = 1;
        if (c + 1 <= N) a[r][c + 1] = 1;
        if (r + 1 <= N) a[r + 1][c] = 1;
        if (r + 1 <= N && c + 1 <= N) a[r + 1][c + 1] = 1;
        if (r + 2 <= N && c + 1 <= N) a[r + 2][c + 1] = 1; // padding step
        r += 2; c += 1; // S_{i+1}
    }

    // Create bridging walkways for bits set in x
    for (int i = 0; i < k; ++i) {
        if ((x >> i) & 1ULL) {
            int rr = 2 * i + 1;
            int cc = i + 1;
            for (int col = cc; col <= min(B, N); ++col) a[rr][col] = 1;
            if (V <= N) a[rr][V] = 1; // connect to vertical line
        }
    }

    // Vertical line (single path downwards)
    if (V <= N) {
        for (int row = 1; row <= N; ++row) a[row][V] = 1;
    }

    // Bottom row path to the sink
    for (int col = V; col <= N; ++col) a[N][col] = 1;

    // Output grid
    cout << N << "\n";
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            cout << a[i][j] << (j == N ? '\n' : ' ');
        }
    }

    return 0;
}