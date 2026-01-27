#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        if(!(cin >> n)) return 0;

        int p = 1;
        int i0 = (n >= 2 ? 2 : 1); // n >= 3 by constraints, so i0=2

        vector<int> r(n + 1, -1), c(n + 1, -1);
        vector<int> row_i0(n + 1, -1);

        // Step A: Query ? i 1 for all i != 1
        for (int i = 1; i <= n; ++i) {
            if (i == p) continue;
            cout << "? " << i << " " << p << endl;
            cout.flush();
            int ans;
            if(!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            r[i] = ans;
        }

        // Step B: Query row i0 to all columns except 1 and i0
        for (int j = 1; j <= n; ++j) {
            if (j == i0 || j == p) continue;
            cout << "? " << i0 << " " << j << endl;
            cout.flush();
            int ans;
            if(!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            row_i0[j] = ans;
        }

        // Compute c[j] for j != i0
        int b = r[i0]; // a_{i0,1}
        for (int j = 1; j <= n; ++j) {
            if (j == i0) continue;
            if (j == p) c[j] = 0;
            else c[j] = row_i0[j] ^ b;
        }

        // Step C: Get c[i0] via any k != 1, i0 with known r[k]
        int k = (i0 == 2 ? 3 : 2); // since n >= 3, this is valid
        cout << "? " << k << " " << i0 << endl;
        cout.flush();
        {
            int ans;
            if(!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            c[i0] = r[k] ^ ans;
        }

        // Step D: Get r[1] via ? 1 i0
        cout << "? " << 1 << " " << i0 << endl;
        cout.flush();
        {
            int ans;
            if(!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            r[1] = ans ^ c[i0];
        }

        // Compute d[j] = r[j] XOR c[j], impostor is unique j with d[j] == 0
        int impostor = -1;
        for (int j = 1; j <= n; ++j) {
            int dj = (r[j] ^ c[j]);
            if (dj == 0) {
                impostor = j;
                break; // Should be unique; we can take the first
            }
        }
        if (impostor == -1) impostor = 1; // fallback, though this should not happen

        cout << "! " << impostor << endl;
        cout.flush();
    }
    return 0;
}