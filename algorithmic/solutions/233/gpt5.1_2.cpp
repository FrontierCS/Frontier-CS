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
        vector<int> vals;
        vals.reserve(n * n);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x;
                cin >> x;
                vals.push_back(x);
            }
        }
        sort(vals.begin(), vals.end());
        cout << "!";
        int cnt = min<long long>(m, (long long)vals.size());
        for (int i = 0; i < cnt; ++i) {
            cout << ' ' << vals[i];
        }
        // If m > n^2, pad arbitrarily with largest value to match count
        for (int i = cnt; i < m; ++i) {
            cout << ' ' << vals.back();
        }
        cout << "\n";
    }
    return 0;
}