#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int MAXK = 10000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> a(N);
    for (int i = 0; i < N; ++i) {
        a[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) cin >> a[i][j];
    }

    auto compute_E = [&]() -> int {
        int E = 0;
        for (int x = 0; x <= N - 2; ++x) {
            for (int y = 0; y <= x; ++y) {
                int p = a[x][y];
                if (p > a[x + 1][y]) ++E;
                if (p > a[x + 1][y + 1]) ++E;
            }
        }
        return E;
    };

    vector<array<int,4>> ops;
    ops.reserve(MAXK);

    auto try_swap = [&](int x1, int y1, int x2, int y2) {
        if ((int)ops.size() >= MAXK) return false;
        swap(a[x1][y1], a[x2][y2]);
        ops.push_back({x1, y1, x2, y2});
        return true;
    };

    auto pass_bottom_up = [&]() -> int {
        int cnt = 0;
        for (int x = N - 2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                if ((int)ops.size() >= MAXK) return cnt;
                int p = a[x][y];
                int cL = a[x + 1][y];
                int cR = a[x + 1][y + 1];
                if (p <= cL && p <= cR) continue;
                if (cL < cR) {
                    if (!try_swap(x, y, x + 1, y)) return cnt;
                } else {
                    if (!try_swap(x, y, x + 1, y + 1)) return cnt;
                }
                ++cnt;
            }
        }
        return cnt;
    };

    auto pass_top_down = [&]() -> int {
        int cnt = 0;
        for (int x = 0; x <= N - 2; ++x) {
            for (int y = 0; y <= x; ++y) {
                if ((int)ops.size() >= MAXK) return cnt;
                int p = a[x][y];
                int cL = a[x + 1][y];
                int cR = a[x + 1][y + 1];
                if (p <= cL && p <= cR) continue;
                if (cL < cR) {
                    if (!try_swap(x, y, x + 1, y)) return cnt;
                } else {
                    if (!try_swap(x, y, x + 1, y + 1)) return cnt;
                }
                ++cnt;
            }
        }
        return cnt;
    };

    int E = compute_E();

    while (E > 0 && (int)ops.size() < MAXK) {
        int s1 = pass_bottom_up();
        E = compute_E();
        if (E == 0 || (int)ops.size() >= MAXK) break;
        int s2 = pass_top_down();
        E = compute_E();
        if (s1 == 0 && s2 == 0) break;
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}