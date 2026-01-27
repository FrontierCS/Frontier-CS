#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        // Initial Type 1 query on all nodes
        cout << "? 1 " << n;
        for (int i = 1; i <= n; ++i) cout << " " << i;
        cout << endl;
        cout.flush();

        long long Tcur;
        if (!(cin >> Tcur)) return 0;

        vector<int> init_val(n + 1, 0);

        for (int i = 1; i <= n; ++i) {
            // Toggle node i
            cout << "? 2 " << i << endl;
            cout.flush();

            // Query sum over all nodes again
            cout << "? 1 " << n;
            for (int j = 1; j <= n; ++j) cout << " " << j;
            cout << endl;
            cout.flush();

            long long Tnew;
            if (!(cin >> Tnew)) return 0;

            long long delta = Tnew - Tcur;
            long long P = -delta / 2; // P = init_val[i] * subtree_size(i), subtree size >= 1
            init_val[i] = (P > 0 ? 1 : -1);

            Tcur = Tnew;
        }

        // After toggling each node once, final values are -init_val[i]
        cout << "!";
        for (int i = 1; i <= n; ++i) {
            cout << " " << -init_val[i];
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}