#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) break;
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
        }
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 1;
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}