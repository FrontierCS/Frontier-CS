#include <bits/stdc++.h>
using namespace std;

int main() {
    const int n = 20, m = 20;
    vector<string> grid(n, string(m, '0'));
    int cx = 10, cy = 10; // center

    // Ensure indices in range [0,19]
    cx = max(0, min(n-1, cx));
    cy = max(0, min(m-1, cy));

    // Mark the center
    grid[cx][cy] = '1';

    // Draw vertical arm
    for (int x = 0; x < n; ++x) grid[x][cy] = '1';

    // Draw horizontal arm
    for (int y = 0; y < m; ++y) grid[cx][y] = '1';

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}