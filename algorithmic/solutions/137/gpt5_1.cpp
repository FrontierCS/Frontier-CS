#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    int row = 10, col = 10;

    // Cross: full row and full column
    for (int y = 0; y < m; ++y) g[row][y] = '1';
    for (int x = 0; x < n; ++x) g[x][col] = '1';

    // Add leaves above and below the row at even columns, excluding the center column
    for (int y = 0; y < m; ++y) {
        if (y % 2 == 0 && y != col) {
            if (row - 1 >= 0) g[row - 1][y] = '1';
            if (row + 1 < n) g[row + 1][y] = '1';
        }
    }

    // Add leaves left and right of the column at odd rows, excluding rows adjacent to center (to avoid 2x2 squares)
    for (int x = 0; x < n; ++x) {
        if (x % 2 == 1 && x != row - 1 && x != row + 1) {
            if (col - 1 >= 0) g[x][col - 1] = '1';
            if (col + 1 < m) g[x][col + 1] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}