#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x; cin >> x;
            }
        }

        int Q = n * (2 * n - 1);
        vector<int> vals;
        vals.reserve(Q);

        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << "\n";
                cout.flush();
                int x;
                if(!(cin >> x)) x = 0;
                vals.push_back(x);
            }
        }

        nth_element(vals.begin(), vals.begin() + min(m, (int)vals.size()) - 1, vals.end());
        sort(vals.begin(), vals.begin() + min(m, (int)vals.size()));

        cout << "! ";
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << vals[i];
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}