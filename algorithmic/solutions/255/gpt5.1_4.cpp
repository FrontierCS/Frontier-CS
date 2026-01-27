#include <bits/stdc++.h>
using namespace std;

int query(int i, int j) {
    cout << "? 1 1\n";
    cout << i << "\n";
    cout << j << "\n";
    cout.flush();
    int F;
    if (!(cin >> F)) exit(0);
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int g1 = -1, g2 = -1;
        bool found = false;

        // Find two non-zero magnets
        for (int i = 1; i <= n && !found; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                int F = query(i, j);
                if (F != 0) {
                    g1 = i;
                    g2 = j;
                    found = true;
                    break;
                }
            }
        }

        vector<int> zeros;

        if (!found) {
            // Theoretically impossible due to constraints (at least 2 non-zero),
            // but handle gracefully.
            for (int i = 1; i <= n; ++i) zeros.push_back(i);
        } else {
            // Classify all magnets using g1 as reference
            for (int k = 1; k <= n; ++k) {
                if (k == g1 || k == g2) continue;
                int F = query(g1, k);
                if (F == 0) zeros.push_back(k);
            }
        }

        cout << "! " << zeros.size();
        for (int x : zeros) cout << ' ' << x;
        cout << "\n";
        cout.flush();
    }

    return 0;
}