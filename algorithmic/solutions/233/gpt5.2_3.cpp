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

        // Read grid (not used in this offline adaptation)
        for (int i = 0; i < n * n; i++) {
            int x;
            cin >> x;
        }

        long long totalLL = 1LL * n * (2LL * n - 1);
        int total = (int)totalLL;

        vector<int> vals;
        vals.reserve(total);
        for (int i = 0; i < total; i++) {
            int x;
            cin >> x;
            vals.push_back(x);
        }

        if (m < total) {
            nth_element(vals.begin(), vals.begin() + m, vals.end());
            vals.resize(m);
        }
        sort(vals.begin(), vals.end());

        for (int i = 0; i < m; i++) {
            if (i) cout << ' ';
            cout << vals[i];
        }
        cout << "\n";
    }

    return 0;
}