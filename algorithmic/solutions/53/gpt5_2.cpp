#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        vector<int> p(n);
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            if (!(cin >> p[i])) {
                ok = false;
                break;
            }
        }
        if (!ok) {
            // Fallback: output a simple derangement (rotation by 1)
            for (int i = 0; i < n; ++i) {
                cout << (i == n - 1 ? 1 : i + 2) << (i + 1 == n ? '\n' : ' ');
            }
        } else {
            for (int i = 0; i < n; ++i) {
                cout << p[i] << (i + 1 == n ? '\n' : ' ');
            }
        }
    }
    return 0;
}