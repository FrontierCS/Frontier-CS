#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    vector<vector<int>> b(N);
    for (int x = 0; x < N; ++x) {
        b[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) {
            if (!(cin >> b[x][y])) return 0;
        }
    }

    const int MAX_OPS = 10000;
    const int MAX_ITERS = 20;
    vector<array<int,4>> ops;
    ops.reserve(MAX_OPS);

    auto do_swap = [&](int x1, int y1, int x2, int y2) {
        swap(b[x1][y1], b[x2][y2]);
        ops.push_back({x1, y1, x2, y2});
    };

    for (int iter = 0; iter < MAX_ITERS && (int)ops.size() < MAX_OPS; ++iter) {
        bool moved = false;
        for (int x = N - 2; x >= 0 && (int)ops.size() < MAX_OPS; --x) {
            for (int y = 0; y <= x && (int)ops.size() < MAX_OPS; ++y) {
                int a0 = b[x][y];
                int b1 = b[x + 1][y];
                int c1 = b[x + 1][y + 1];
                if (a0 > b1 || a0 > c1) {
                    if (b1 <= c1) {
                        do_swap(x, y, x + 1, y);
                    } else {
                        do_swap(x, y, x + 1, y + 1);
                    }
                    moved = true;
                }
            }
        }
        if (!moved) break;
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}