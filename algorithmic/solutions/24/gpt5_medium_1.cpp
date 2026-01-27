#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<vector<char>> C(n+1, vector<char>(n+1, 0));
        for (int i = 1; i <= n; ++i) {
            string s;
            if (!(cin >> s)) return 0;
            if ((int)s.size() == n) {
                for (int j = 1; j <= n; ++j) C[i][j] = s[j-1] - '0';
            } else {
                C[i][1] = s[0] - '0';
                for (int j = 2; j <= n; ++j) {
                    string t; cin >> t;
                    C[i][j] = t[0] - '0';
                }
            }
        }
        vector<int> p(n);
        iota(p.begin(), p.end(), 1);
        if (n >= 3) {
            int i = 0;
            while (i <= n - 3) {
                int a = p[i], b = p[i+1], c = p[i+2];
                if (C[a][b] > C[b][c]) {
                    swap(p[i+1], p[i+2]);
                    if (i > 0) --i;
                } else {
                    ++i;
                }
            }
        }
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    }
    return 0;
}