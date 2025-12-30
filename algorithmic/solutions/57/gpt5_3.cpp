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

        vector<int> init(n + 1, 0);

        for (int v = 1; v <= n; ++v) {
            cout << "? 1 1 " << v << "\n";
            cout.flush();
            long long f1;
            if (!(cin >> f1)) return 0;

            cout << "? 2 " << v << "\n";
            cout.flush();

            cout << "? 1 1 " << v << "\n";
            cout.flush();
            long long f2;
            if (!(cin >> f2)) return 0;

            long long delta = f2 - f1;
            int av0 = (int)(-delta / 2);
            if (av0 != 1 && av0 != -1) {
                // In case of unexpected response, attempt to clamp
                av0 = (delta == 0 ? 1 : (delta > 0 ? -1 : 1));
            }
            init[v] = av0;
        }

        cout << "!";
        for (int i = 1; i <= n; ++i) {
            cout << " " << -init[i];
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}