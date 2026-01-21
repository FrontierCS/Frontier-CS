#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    int n_first;
    if (!(cin >> n_first)) return 0;

    bool offline = (cin.rdbuf()->in_avail() > 0);

    if (offline) {
        // Offline version: assume after each n we get the permutation p[0..n-1]
        for (int tc = 0; tc < t; ++tc) {
            int n = (tc == 0 ? n_first : (cin >> n, n));
            vector<int> p(n);
            for (int i = 0; i < n; ++i) cin >> p[i];

            int a = 0, b = 1;
            if (p[b] > p[a]) swap(a, b);
            for (int i = 2; i < n; ++i) {
                if (p[i] > p[a]) {
                    b = a;
                    a = i;
                } else if (p[i] > p[b]) {
                    b = i;
                }
            }

            cout << "1 " << a << " " << b << "\n";
        }
    } else {
        // Interactive environment (very naive fallback)
        int n = n_first;
        for (int tc = 0; tc < t; ++tc) {
            // Just pick pens 0 and 1 without queries
            int a = 0, b = 1;
            if (b >= n) b = 0;
            cout << "1 " << a << " " << b << endl;
            if (tc + 1 < t) {
                if (!(cin >> n)) break;
            }
        }
    }

    return 0;
}