#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> grid(n, string(m, '0'));

    for (int r = 0; r < n; ++r) {
        if (r % 2 == 0) {
            // Even rows fully open
            for (int c = 0; c < m; ++c) grid[r][c] = '1';
        } else {
            // Odd rows: single connector at alternating ends
            int c = (((r - 1) / 2) % 2 == 0) ? (m - 1) : 0;
            grid[r][c] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}