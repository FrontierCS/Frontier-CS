#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> grid(n, string(m, '0'));

    // Fill even columns with '1's to form vertical segments
    for (int c = 0; c < m; c += 2) {
        for (int r = 0; r < n; ++r) {
            grid[r][c] = '1';
        }
    }

    // Connect the vertical segments alternately at bottom and top with single-cell bridges
    for (int c = 0; c + 2 < m; c += 2) {
        if (((c / 2) % 2) == 0) {
            // Connect at bottom row
            grid[n - 1][c + 1] = '1';
        } else {
            // Connect at top row
            grid[0][c + 1] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int r = 0; r < n; ++r) {
        cout << grid[r] << "\n";
    }
    return 0;
}