#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<vector<int>> G(n + 1, vector<int>(n + 1));
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                cin >> G[i][j];
            }
        }
        vector<int> all_f;
        for (int l = 1; l <= n; ++l) {
            vector<int> fl(2 * n);
            // T = 1
            int mx = INT_MIN;
            for (int j = 1; j <= l; ++j) {
                mx = max(mx, G[1][j]);
            }
            fl[1] = mx;
            // T = 2
            mx = G[2][1];
            for (int j = 1; j <= l - 1; ++j) {
                mx = max(mx, G[1][j]);
            }
            fl[2] = mx;
            // T = 3 to 2n-1
            for (int T = 3; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << endl;
                cout.flush();
                int val;
                cin >> val;
                fl[T] = val;
            }
            for (int T = 1; T <= 2 * n - 1; ++T) {
                all_f.push_back(fl[T]);
            }
        }
        sort(all_f.begin(), all_f.end());
        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << " " << all_f[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}