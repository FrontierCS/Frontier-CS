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

        vector<int> x(n + 1, 0), y(n + 1, 0);

        // Queries: row 1 to all other columns
        for (int j = 2; j <= n; ++j) {
            cout << "? 1 " << j << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            x[j] = ans;
        }

        // Queries: all other rows to column 1
        for (int i = 2; i <= n; ++i) {
            cout << "? " << i << " 1" << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            y[i] = ans;
        }

        int c00 = 0, c01 = 0, c10 = 0, c11 = 0;
        int idx01 = -1, idx10 = -1;

        for (int i = 2; i <= n; ++i) {
            int xi = x[i], yi = y[i];
            if (xi == 0 && yi == 0) {
                ++c00;
            } else if (xi == 0 && yi == 1) {
                ++c01;
                if (idx01 == -1) idx01 = i;
            } else if (xi == 1 && yi == 0) {
                ++c10;
                if (idx10 == -1) idx10 = i;
            } else { // xi == 1 && yi == 1
                ++c11;
            }
        }

        int K0 = (3 * n) / 10 + 1; // floor(0.3 * n) + 1

        bool validA = (c01 == 0 && c10 == 1 && 1 + c11 >= K0);
        bool validB = (c10 == 0 && c01 == 1 && c00 >= K0);
        bool validC = (c00 == 0 && c11 == 0 && c01 >= K0);

        int impostor = -1;
        if (validA) impostor = idx10;
        if (validB) impostor = idx01;
        if (validC) impostor = 1;

        if (impostor == -1) impostor = 1; // Fallback, should not occur with valid interactor

        cout << "! " << impostor << endl;
        cout.flush();
    }

    return 0;
}