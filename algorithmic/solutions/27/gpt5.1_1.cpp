#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<pair<int,int>> ans;

    // 1D cases: no rectangle possible
    if (n == 1 || m == 1) {
        ans.reserve(1LL * n * m);
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= m; ++j)
                ans.emplace_back(i, j);
    }
    // 2-row grid: n == 2, m >= 2
    else if (n == 2 && m >= 2) {
        ans.reserve(2LL * m);
        // First column: both rows
        ans.emplace_back(1, 1);
        ans.emplace_back(2, 1);
        // Remaining columns: single row alternating
        for (int c = 2; c <= m; ++c) {
            int r = (c % 2 == 0 ? 1 : 2);
            ans.emplace_back(r, c);
        }
    }
    // 2-column grid: m == 2, n >= 2
    else if (m == 2 && n >= 2) {
        ans.reserve(2LL * n);
        // First row: both columns
        ans.emplace_back(1, 1);
        ans.emplace_back(1, 2);
        // Remaining rows: single column alternating
        for (int r = 2; r <= n; ++r) {
            int c = (r % 2 == 0 ? 1 : 2);
            ans.emplace_back(r, c);
        }
    }
    // General case: min(n, m) >= 3
    else {
        int s, t;
        bool rowSmall;
        if (n <= m) {
            rowSmall = true;
            s = n;      // smaller side = rows
            t = m;      // larger side = columns
        } else {
            rowSmall = false;
            s = m;      // smaller side = columns
            t = n;      // larger side = rows
        }

        // Degree cap per vertex on the large side
        int Dmax = (int)(sqrt((double)s) + 0.5);
        if (Dmax < 2) Dmax = 2;
        if (Dmax > s) Dmax = s;

        vector<char> pairUsed((size_t)s * s, 0);
        vector<vector<int>> neighB(t);
        ans.reserve(1LL * n * m);

        if (rowSmall) {
            // A = rows [0..s-1], B = columns [0..t-1]
            for (int b = 0; b < t; ++b) {
                auto &rows = neighB[b];
                int deg = 0;
                int start = b % s;
                for (int off = 0; off < s && deg < Dmax; ++off) {
                    int a = start + off;
                    if (a >= s) a -= s;

                    bool ok = true;
                    for (int prev : rows) {
                        int x = (a < prev ? a : prev);
                        int y = (a < prev ? prev : a);
                        if (pairUsed[(size_t)x * s + y]) {
                            ok = false;
                            break;
                        }
                    }
                    if (!ok) continue;

                    for (int prev : rows) {
                        int x = (a < prev ? a : prev);
                        int y = (a < prev ? prev : a);
                        pairUsed[(size_t)x * s + y] = 1;
                    }
                    rows.push_back(a);
                    ++deg;
                    ans.emplace_back(a + 1, b + 1);
                }
            }
        } else {
            // A = columns [0..s-1], B = rows [0..t-1]
            for (int b = 0; b < t; ++b) {
                auto &cols = neighB[b];
                int deg = 0;
                int start = b % s;
                for (int off = 0; off < s && deg < Dmax; ++off) {
                    int a = start + off;
                    if (a >= s) a -= s;

                    bool ok = true;
                    for (int prev : cols) {
                        int x = (a < prev ? a : prev);
                        int y = (a < prev ? prev : a);
                        if (pairUsed[(size_t)x * s + y]) {
                            ok = false;
                            break;
                        }
                    }
                    if (!ok) continue;

                    for (int prev : cols) {
                        int x = (a < prev ? a : prev);
                        int y = (a < prev ? prev : a);
                        pairUsed[(size_t)x * s + y] = 1;
                    }
                    cols.push_back(a);
                    ++deg;
                    ans.emplace_back(b + 1, a + 1);
                }
            }
        }
    }

    cout << ans.size() << '\n';
    for (auto &p : ans) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}