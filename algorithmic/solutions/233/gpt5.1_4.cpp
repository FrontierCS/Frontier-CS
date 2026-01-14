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
        // Read grid (unused)
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x;
                cin >> x;
            }
        }
        int total = n * (2 * n - 1);
        vector<int> vals;
        vals.reserve(total);
        for (int i = 0; i < total; ++i) {
            int x;
            cin >> x;
            vals.push_back(x);
        }
        nth_element(vals.begin(), vals.begin() + m, vals.end());
        vals.resize(m);
        sort(vals.begin(), vals.end());
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << vals[i];
        }
        cout << '\n';
    }
    return 0;
}