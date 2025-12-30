#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 30;
    vector<vector<int>> g(N);
    for (int i = 0; i < N; i++) {
        g[i].resize(i + 1);
        for (int j = 0; j <= i; j++) {
            if (!(cin >> g[i][j])) return 0;
        }
    }

    vector<array<int, 4>> ops;
    ops.reserve(10000);
    int K = 0;

    auto do_swap = [&](int x1, int y1, int x2, int y2) {
        if (K >= 10000) return false;
        swap(g[x1][y1], g[x2][y2]);
        ops.push_back({x1, y1, x2, y2});
        K++;
        return true;
    };

    while (K < 10000) {
        bool any = false;
        for (int x = N - 2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                int v = g[x][y];
                int c1 = g[x + 1][y];
                int c2 = g[x + 1][y + 1];
                if (c1 < v || c2 < v) {
                    if (c1 <= c2) {
                        if (!do_swap(x, y, x + 1, y)) goto OUTPUT;
                        any = true;
                    } else {
                        if (!do_swap(x, y, x + 1, y + 1)) goto OUTPUT;
                        any = true;
                    }
                }
                if (K >= 10000) goto OUTPUT;
            }
        }
        if (!any) break;
    }

OUTPUT:
    cout << K << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}