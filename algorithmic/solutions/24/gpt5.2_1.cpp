#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        vector<string> mat(n, string(n, '0'));
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                char ch;
                cin >> ch;
                while (ch != '0' && ch != '1') cin >> ch;
                mat[i][j] = ch;
            }
        }

        auto col = [&](int u, int v) -> int {
            return mat[u][v] - '0';
        };

        int pivot = 0;
        vector<int> L, R; // L: 0-path from pivot; R: 1-path from pivot

        for (int v = 1; v < n; v++) {
            bool canL = L.empty() ? (col(pivot, v) == 0) : (col(L.back(), v) == 0);
            if (canL) {
                L.push_back(v);
                continue;
            }
            bool canR = R.empty() ? (col(pivot, v) == 1) : (col(R.back(), v) == 1);
            if (canR) {
                R.push_back(v);
                continue;
            }

            if (L.empty()) {
                // pivot-v is 1 and R.back-v is 0
                int newPivot = R.back();
                R.pop_back();
                reverse(R.begin(), R.end());
                R.push_back(pivot);
                pivot = newPivot;
                // now pivot-v is 0
                L.push_back(v);
                continue;
            }
            if (R.empty()) {
                // pivot-v is 0 and L.back-v is 1
                int newPivot = L.back();
                L.pop_back();
                reverse(L.begin(), L.end());
                L.push_back(pivot);
                pivot = newPivot;
                // now pivot-v is 1
                R.push_back(v);
                continue;
            }

            int endL = L.back();
            int endR = R.back();
            if (col(endL, endR) == 0) {
                R.pop_back();
                L.push_back(endR);
                L.push_back(v);
            } else {
                L.pop_back();
                R.push_back(endL);
                R.push_back(v);
            }
        }

        // Build a cycle list (circular order) with at most 2 color changes.
        vector<int> cyc;
        cyc.reserve(n);

        int a = L.empty() ? pivot : L.back();
        cyc.push_back(a);
        if (!L.empty()) {
            for (int i = (int)L.size() - 2; i >= 0; i--) cyc.push_back(L[i]);
            cyc.push_back(pivot);
        }
        for (int x : R) cyc.push_back(x);

        if ((int)cyc.size() != n) {
            cout << -1 << "\n";
            continue;
        }

        // Rotate cycle to make linear changes <= 1 (ignore last-first comparison).
        vector<int> e(n);
        for (int i = 0; i < n; i++) {
            e[i] = col(cyc[i], cyc[(i + 1) % n]);
        }
        int start = 0;
        for (int i = 0; i < n; i++) {
            if (e[i] != e[(i + 1) % n]) {
                start = (i + 1) % n;
                break;
            }
        }

        vector<int> perm(n);
        for (int i = 0; i < n; i++) perm[i] = cyc[(start + i) % n];

        // Validate (safety).
        vector<int> c(n);
        for (int i = 0; i < n; i++) {
            c[i] = col(perm[i], perm[(i + 1) % n]);
        }
        int changes = 0;
        for (int i = 0; i < n - 1; i++) changes += (c[i] != c[i + 1]);
        if (changes > 1) {
            cout << -1 << "\n";
            continue;
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << (perm[i] + 1);
        }
        cout << "\n";
    }

    return 0;
}