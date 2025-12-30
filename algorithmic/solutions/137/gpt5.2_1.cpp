#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    // Even rows: fully empty
    for (int r = 0; r < n; r += 2) {
        for (int c = 0; c < m; c++) g[r][c] = '1';
    }

    // Connectors between even rows, alternating ends to form a long path
    for (int k = 0; k < 9; k++) {
        int r = 2 * k + 1;
        int c = (k % 2 == 0) ? (m - 1) : 0;
        g[r][c] = '1';
    }

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; i++) cout << g[i] << "\n";
    return 0;
}