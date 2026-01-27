#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        vector<string> mat(n);
        for (int i = 0; i < n; ++i) {
            string row;
            row.reserve(n);
            while ((int)row.size() < n) {
                string tmp;
                if (!(cin >> tmp)) return 0;
                row += tmp;
            }
            if ((int)row.size() > n) row.resize(n);
            mat[i] = row;
        }

        vector<int> perm;
        perm.reserve(n);

        for (int v = 1; v <= n; ++v) {
            if (perm.empty()) {
                perm.push_back(v);
                continue;
            }
            if ((int)perm.size() == 1) {
                perm.push_back(v);
                continue;
            }

            int m = (int)perm.size();

            // Precompute edge colors along current path
            static vector<char> c, a;
            c.assign(m - 1, 0);
            a.assign(m, 0);

            for (int i = 0; i < m - 1; ++i) {
                int u = perm[i] - 1;
                int w = perm[i + 1] - 1;
                c[i] = mat[u][w];
            }

            int T_old = 0;
            for (int i = 0; i < m - 2; ++i) {
                if (c[i] != c[i + 1]) ++T_old;
            }

            for (int i = 0; i < m; ++i) {
                int u = perm[i] - 1;
                a[i] = mat[v - 1][u];
            }

            int bestPos = -1;

            for (int j = 0; j <= m; ++j) {
                int T_new;
                if (j == 0) {
                    // Insert at front
                    if (m == 1) {
                        T_new = 0;
                    } else {
                        T_new = T_old + (a[0] != c[0]);
                    }
                } else if (j == m) {
                    // Insert at end
                    if (m == 1) {
                        T_new = 0;
                    } else {
                        T_new = T_old + (c[m - 2] != a[m - 1]);
                    }
                } else {
                    // Insert between perm[j-1] and perm[j]
                    int E = 0, F = 0;
                    if (j - 2 >= 0) {
                        if (c[j - 2] != c[j - 1]) ++E;
                        if (c[j - 2] != a[j - 1]) ++F;
                    }
                    if (j - 1 <= m - 3) {
                        if (c[j - 1] != c[j]) ++E;
                    }
                    char L = a[j - 1];
                    char R = a[j];
                    if (L != R) ++F;
                    if (j <= m - 2) {
                        if (R != c[j]) ++F;
                    }
                    T_new = T_old - E + F;
                }

                if (T_new <= 1) {
                    bestPos = j;
                    break;
                }
            }

            if (bestPos == -1) bestPos = m; // Should not happen
            perm.insert(perm.begin() + bestPos, v);
        }

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << '\n';
    }

    return 0;
}