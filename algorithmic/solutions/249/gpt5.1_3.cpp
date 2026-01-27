#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Read all pairwise ORs for 1 <= i < j <= n
    vector<vector<int>> ORv(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            int x;
            cin >> x;
            ORv[i][j] = ORv[j][i] = x;
        }
    }

    const int MASK = (1 << 11) - 1; // since n <= 2048, numbers < 2^11

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int val = MASK;
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            val &= ORv[i][j];
        }
        p[i] = val;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}