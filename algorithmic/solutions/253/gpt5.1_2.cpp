#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        if (!(cin >> n >> m)) return 0;
        for (int i = 0; i < m; ++i) {
            int a, b;
            cin >> a >> b;
        }
        cout << "!";
        for (int i = 0; i < m; ++i) cout << " 0";
        cout << "\n";
        cout.flush();
    }

    return 0;
}