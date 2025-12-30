#include <bits/stdc++.h>
using namespace std;

int main() {
    const int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    for (int r = 0; r <= 18; r += 2) {
        for (int c = 0; c < m; c++) g[r][c] = '1';
    }

    for (int r = 1; r <= 17; r += 2) {
        int col = ((r / 2) % 2 == 0) ? (m - 1) : 0;
        g[r][col] = '1';
    }

    for (int c = 0; c < m; c += 2) g[19][c] = '1';

    cout << n << " " << m << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}