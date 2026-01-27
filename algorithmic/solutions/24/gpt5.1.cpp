#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        vector<vector<int>> C(n, vector<int>(n));
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                char ch;
                cin >> ch;
                while (ch != '0' && ch != '1') {
                    if (!(cin >> ch)) break;
                }
                C[i][j] = ch - '0';
            }
        }
        for (int i = 1; i <= n; ++i) {
            cout << i << (i == n ? '\n' : ' ');
        }
    }
    return 0;
}