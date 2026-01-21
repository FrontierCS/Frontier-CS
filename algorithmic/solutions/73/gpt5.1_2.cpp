#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << 1 << " " << 1 << '\n';
        cout.flush();
        return 0;
    }

    vector<vector<int>> inv(n + 2, vector<int>(n + 2, 0));

    // Query all segments [l, r] with length >= 2
    for (int len = 2; len <= n; ++len) {
        for (int l = 1; l + len - 1 <= n; ++l) {
            int r = l + len - 1;
            cout << 0 << " " << l << " " << r << '\n';
            cout.flush();
            int x;
            if (!(cin >> x)) return 0;
            if (x < 0) return 0;  // in case of judge error signal
            inv[l][r] = x & 1;
        }
    }

    vector<int> rankv(n + 1, 1);
    for (int i = 1; i <= n; ++i) rankv[i] = 1;

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int a = inv[i][j];
            int b = inv[i + 1][j];
            int c = inv[i][j - 1];
            int d = inv[i + 1][j - 1]; // zero if indices invalid (l >= r), as initialized
            int bit = a ^ b ^ c ^ d;   // 1 if pi > pj, 0 otherwise
            if (bit) {
                ++rankv[i];
            } else {
                ++rankv[j];
            }
        }
    }

    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << " " << rankv[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}