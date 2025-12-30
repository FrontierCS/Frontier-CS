#include <bits/stdc++.h>
using namespace std;

int main() {
    const int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    for (int i = 0; i < 10; i++) {
        int r = 2 * i;
        for (int c = 0; c < m; c++) g[r][c] = '1';
        if (i < 9) {
            int cr = r + 1;
            int cc = (i % 2 == 0) ? (m - 1) : 0;
            g[cr][cc] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int r = 0; r < n; r++) cout << g[r] << "\n";
    return 0;
}