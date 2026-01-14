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
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x; cin >> x;
            }
        }
        vector<int> vals;
        vals.reserve(n * (2 * n - 1));
        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << "\n";
                int x;
                cin >> x;
                vals.push_back(x);
            }
        }
        if (m >= (int)vals.size()) {
            sort(vals.begin(), vals.end());
            cout << "!";
            for (int i = 0; i < m; ++i) cout << " " << vals[i];
            cout << "\n";
        } else {
            nth_element(vals.begin(), vals.begin() + m, vals.end());
            vector<int> res(vals.begin(), vals.begin() + m);
            sort(res.begin(), res.end());
            cout << "!";
            for (int i = 0; i < m; ++i) cout << " " << res[i];
            cout << "\n";
        }
    }
    return 0;
}