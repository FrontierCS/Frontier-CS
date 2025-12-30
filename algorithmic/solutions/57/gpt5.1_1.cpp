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
        // Read and ignore tree edges
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }

        vector<int> val(n + 1);

        // Initial query: sum of f(u) over all nodes
        cout << "? 1 " << n;
        for (int i = 1; i <= n; ++i) cout << ' ' << i;
        cout << endl;
        cout.flush();

        long long S_prev;
        if (!(cin >> S_prev)) return 0;

        for (int i = 1; i <= n; ++i) {
            // Toggle node i
            cout << "? 2 " << i << endl;
            cout.flush();

            // Query new global sum after toggle
            cout << "? 1 " << n;
            for (int j = 1; j <= n; ++j) cout << ' ' << j;
            cout << endl;
            cout.flush();

            long long S_new;
            if (!(cin >> S_new)) return 0;
            long long delta = S_new - S_prev;

            if (delta > 0) val[i] = 1;
            else if (delta < 0) val[i] = -1;
            else val[i] = 1; // Should not occur

            S_prev = S_new;
        }

        // Output final values
        cout << '!';
        for (int i = 1; i <= n; ++i) cout << ' ' << val[i];
        cout << endl;
        cout.flush();
    }

    return 0;
}