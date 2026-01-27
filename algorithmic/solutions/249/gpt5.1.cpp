#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> OR(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int x;
            cin >> x;
            OR[i][j] = OR[j][i] = x;
        }
    }

    const int MAXV = (1 << 11) - 1; // since n <= 2048, max value is 2047
    vector<int> p(n);

    for (int i = 0; i < n; ++i) {
        int v = MAXV;
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            v &= OR[i][j];
        }
        p[i] = v;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}