#include <bits/stdc++.h>
using namespace std;

static inline int ask(int i, int j) {
    cout << "? " << i << " " << j << "\n";
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        vector<int> d(n + 1, 0);
        for (int i = 1; i <= n - 1; i++) {
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            d[i] = a ^ b; // D(i) xor D(i+1)
        }

        vector<int> D(n + 1, 0);
        D[1] = 0;
        for (int i = 1; i <= n - 1; i++) D[i + 1] = D[i] ^ d[i];

        int ones = 0;
        for (int i = 1; i <= n; i++) ones += D[i];

        int ans = 1;
        if (ones == 1) {
            for (int i = 1; i <= n; i++) if (D[i] == 1) { ans = i; break; }
        } else if (ones == n - 1) {
            for (int i = 1; i <= n; i++) if (D[i] == 0) { ans = i; break; }
        } else {
            // Should be impossible if interactor respects constraints; pick a safe default.
            ans = 1;
        }

        cout << "! " << ans << "\n";
        cout.flush();
    }
    return 0;
}