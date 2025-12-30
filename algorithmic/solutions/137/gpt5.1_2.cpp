#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));

    // Vertical trunk in column 0
    for (int i = 0; i < n; ++i) {
        g[i][0] = '1';
    }

    // Full horizontal branches on rows with even index (1-based odd rows)
    for (int i = 0; i < n; i += 2) {
        for (int j = 0; j < m; ++j) {
            g[i][j] = '1';
        }
    }

    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}