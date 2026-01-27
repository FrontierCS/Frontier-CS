#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m;
        if (!(cin >> n >> m)) break;
        for (int i = 0; i < m; ++i) {
            int a, b;
            if (!(cin >> a >> b)) return 0;
        }
        cout << "! ";
        for (int i = 0; i < m; ++i) {
            cout << 0;
            if (i + 1 < m) cout << ' ';
        }
        cout << '\n';
        cout.flush();
    }
    return 0;
}