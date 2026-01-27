#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> grid(n, string(m, '0'));

    // Create an L-shaped path:
    // Joint at (10,5), vertical branch upwards to (0,5), horizontal branch to the right to (10,19).
    for (int r = 0; r <= 10; ++r) grid[r][5] = '1';
    for (int c = 5; c < m; ++c) grid[10][c] = '1';

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) cout << grid[i] << "\n";
    return 0;
}