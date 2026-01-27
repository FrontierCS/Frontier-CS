#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<vector<long long>> G(n, vector<long long>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                cin >> G[i][j];

        int totalT = 2 * n - 1;
        vector<long long> vals;
        vals.reserve(n * totalT);

        for (int l = 1; l <= n; ++l) {
            for (int Tt = 1; Tt <= totalT; ++Tt) {
                cout << "? " << l << " " << Tt << endl;
                cout.flush();
                long long x;
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
        cout << endl;
        cout.flush();
    }
    return 0;
}