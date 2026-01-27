#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        vector<int> d(n + 1, 0); // d[i] = c1 * ci for i >= 2

        for (int i = 2; i <= n; ++i) {
            cout << "? " << 1 << " " << i << '\n';
            cout.flush();
            int a1;
            if (!(cin >> a1)) return 0;
            if (a1 == -1) return 0;

            cout << "? " << i << " " << 1 << '\n';
            cout.flush();
            int a2;
            if (!(cin >> a2)) return 0;
            if (a2 == -1) return 0;

            int b1 = a1 ? 1 : -1;
            int b2 = a2 ? 1 : -1;
            d[i] = b1 * b2; // = c1 * ci
        }

        int impostor = 1;
        bool allNeg = true;
        for (int i = 2; i <= n; ++i) {
            if (d[i] != -1) {
                allNeg = false;
                break;
            }
        }

        if (!allNeg) {
            // Exactly one d[i] should be -1
            int cand = -1;
            for (int i = 2; i <= n; ++i) {
                if (d[i] == -1) {
                    cand = i;
                    break;
                }
            }
            if (cand != -1) impostor = cand;
        } else {
            impostor = 1;
        }

        cout << "! " << impostor << '\n';
        cout.flush();
    }
    return 0;
}