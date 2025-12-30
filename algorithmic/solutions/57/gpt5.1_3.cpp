#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        // Read tree edges (not used)
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        vector<int> val(n + 1);

        for (int i = 1; i <= n; ++i) {
            cout << "? 1 1 " << i << endl;
            long long before;
            if (!(cin >> before)) return 0;
            if (before == -1) return 0;

            cout << "? 2 " << i << endl;

            cout << "? 1 1 " << i << endl;
            long long after;
            if (!(cin >> after)) return 0;
            if (after == -1) return 0;

            long long d = before - after;
            int x;
            if (d == 2) x = 1;
            else if (d == -2) x = -1;
            else x = (int)(d / 2); // should still be ±1
            val[i] = x;
        }

        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            int finalVal = -val[i];
            cout << finalVal << (i == n ? '\n' : ' ');
        }
        cout.flush();
    }

    return 0;
}