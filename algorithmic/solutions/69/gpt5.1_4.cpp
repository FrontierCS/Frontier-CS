#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Output n distinct magic words: "X", "XX", ..., "X"*n
    for (int i = 1; i <= n; ++i) {
        cout << string(i, 'X') << "\n";
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;

    while (q--) {
        long long p;
        cin >> p;

        int u = 1, v = 1;

        // For our words, power of "X"^(i+j) is i + j.
        // Choose a canonical pair (u, v) such that u + v = p, if possible.
        if (p >= 2 && p <= 2LL * n) {
            if (p <= n + 1) {
                u = int(p - 1);
                v = 1;
            } else {
                u = n;
                v = int(p - n);
            }
        } else {
            u = v = 1;
        }

        u = max(1, min(u, n));
        v = max(1, min(v, n));

        cout << u << " " << v << "\n";
        cout.flush();
    }

    return 0;
}