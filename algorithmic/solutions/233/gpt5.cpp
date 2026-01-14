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
        vector<vector<int>> G(n, vector<int>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                cin >> G[i][j];

        vector<int> all;
        all.reserve(1LL * n * (2 * n - 1));

        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << "\n";
                cout.flush();
                int val;
                if (!(cin >> val)) return 0;
                all.push_back(val);
            }
        }

        if ((int)all.size() > m) {
            nth_element(all.begin(), all.begin() + m, all.end());
            all.resize(m);
        }
        sort(all.begin(), all.end());

        cout << "!";
        for (int v : all) cout << " " << v;
        cout << "\n";
        cout.flush();
    }
    return 0;
}