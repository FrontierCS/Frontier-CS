#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    int r = 10; // backbone row (0-indexed)
    vector<string> g(n, string(m, '0'));

    for (int c = 0; c < m; ++c) {
        g[r][c] = '1';
        if (c % 2 == 0) {
            for (int i = r - 1; i >= 0; --i) g[i][c] = '1';
        } else {
            for (int i = r + 1; i < n; ++i) g[i][c] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}