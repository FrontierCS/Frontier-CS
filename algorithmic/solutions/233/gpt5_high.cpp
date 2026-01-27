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
        for (int i = 0; i < n * n; ++i) {
            int x; cin >> x; // grid values, not used
        }
        int N = n * (2 * n - 1);
        vector<int> vals(N);
        for (int i = 0; i < N; ++i) cin >> vals[i];

        if (m < N) {
            nth_element(vals.begin(), vals.begin() + m, vals.end());
            sort(vals.begin(), vals.begin() + m);
        } else {
            sort(vals.begin(), vals.end());
        }

        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << vals[i];
        }
        cout << '\n';
    }
    return 0;
}