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
        vals.reserve(1LL * n * (2 * n - 1));
        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= 2 * n - 1; ++T) {
                cout << "? " << l << " " << T << endl;
                cout.flush();
                int resp;
                if (!(cin >> resp)) return 0;
                vals.push_back(resp);
            }
        }
        sort(vals.begin(), vals.end());
        cout << "!";
        for (int i = 0; i < m; ++i) {
            cout << (i == 0 ? ' ' : ' ') << vals[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}