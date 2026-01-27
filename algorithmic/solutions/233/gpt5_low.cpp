#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int _case = 0; _case < t; ++_case) {
        int n, m;
        cin >> n >> m;
        vector<vector<int>> G(n, vector<int>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                cin >> G[i][j];

        vector<int> vals;
        vals.reserve(n * (2 * n - 1));

        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << '\n';
                cout.flush();
                int x;
                if (!(cin >> x)) return 0;
                vals.push_back(x);
            }
        }

        nth_element(vals.begin(), vals.begin() + m, vals.end());
        vals.resize(m);
        sort(vals.begin(), vals.end());

        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << " " << vals[i];
        }
        cout << '\n';
        cout.flush();
    }
    return 0;
}