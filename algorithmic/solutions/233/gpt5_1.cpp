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
        // Read grid (not used directly here)
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x; cin >> x;
            }
        }

        int tot = n * (2 * n - 1);
        vector<int> vals;
        vals.reserve(tot);

        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << "\n";
                cout.flush();
                int resp;
                cin >> resp;
                vals.push_back(resp);
            }
        }

        int M = min(m, (int)vals.size());
        if (M < (int)vals.size()) {
            nth_element(vals.begin(), vals.begin() + M, vals.end());
            vals.resize(M);
        }
        sort(vals.begin(), vals.end());

        cout << "!";
        for (int i = 0; i < M; ++i) {
            cout << " " << vals[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}