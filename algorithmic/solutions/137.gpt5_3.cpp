#include <bits/stdc++.h>
using namespace std;

int main() {
    int n = 20, m = 20;
    vector<string> g(n, string(m, '0'));
    for (int i = 0; i < n; i += 2) {
        for (int j = 0; j < m; ++j) g[i][j] = '1';
        int r = i + 1;
        if (r < n) {
            int endc = (i % 4 == 0) ? (m - 1) : 0;
            g[r][endc] = '1';
        }
    }
    cout << n << " " << m << "\n";
    for (int i = 0; i < n; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}