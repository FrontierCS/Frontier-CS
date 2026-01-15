#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        int m;
        cin >> n >> m;

        // Read grid (unused in offline version)
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int x;
                cin >> x;
            }
        }

        int N = n * (2 * n - 1);
        vector<int> a(N);
        for (int i = 0; i < N; i++) cin >> a[i];

        if (m < N) {
            nth_element(a.begin(), a.begin() + m, a.end());
            a.resize(m);
        }
        sort(a.begin(), a.end());

        for (int i = 0; i < m; i++) {
            if (i) cout << ' ';
            cout << a[i];
        }
        cout << '\n';
    }
    return 0;
}