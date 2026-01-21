#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int MAXB = 11;
    const int fullmask = (1 << MAXB) - 1; // 2047, covers all possible bits (n <= 2048)

    vector<vector<int>> a(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> a[i][j];
        }
    }

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int cur = fullmask;
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            cur &= a[i][j];
        }
        p[i] = cur;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}