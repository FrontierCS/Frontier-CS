#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    const int LIMIT = 10000;

    vector<vector<int>> a(N);
    for (int x = 0; x < N; x++) {
        a[x].resize(x + 1);
        for (int y = 0; y <= x; y++) cin >> a[x][y];
    }

    vector<array<int, 4>> ops;
    ops.reserve(LIMIT);

    auto do_swap = [&](int x1, int y1, int x2, int y2) -> bool {
        if ((int)ops.size() >= LIMIT) return false;
        swap(a[x1][y1], a[x2][y2]);
        ops.push_back({x1, y1, x2, y2});
        return true;
    };

    auto siftDown = [&](int sx, int sy) {
        int x = sx, y = sy;
        while (x < N - 1) {
            int x1 = x + 1, y1 = y;
            int x2 = x + 1, y2 = y + 1;
            int nx = x1, ny = y1;
            if (a[x2][y2] < a[x1][y1]) {
                nx = x2;
                ny = y2;
            }
            if (a[x][y] <= a[nx][ny]) break;
            if (!do_swap(x, y, nx, ny)) return;
            x = nx;
            y = ny;
        }
    };

    auto calcE = [&]() -> int {
        int E = 0;
        for (int x = 0; x < N - 1; x++) {
            for (int y = 0; y <= x; y++) {
                if (a[x][y] > a[x + 1][y]) E++;
                if (a[x][y] > a[x + 1][y + 1]) E++;
            }
        }
        return E;
    };

    // Youngify-style heapify for staircase Young tableau (u=y desc, v=x-y desc).
    for (int y = N - 2; y >= 0 && (int)ops.size() < LIMIT; y--) {
        for (int x = N - 2; x >= y && (int)ops.size() < LIMIT; x--) {
            if (a[x][y] > a[x + 1][y] || a[x][y] > a[x + 1][y + 1]) siftDown(x, y);
        }
    }

    // If still not valid (should be rare), fix remaining violations greedily.
    int E = calcE();
    for (int it = 0; it < 2000 && E > 0 && (int)ops.size() < LIMIT; it++) {
        bool changed = false;
        for (int x = 0; x < N - 1 && (int)ops.size() < LIMIT; x++) {
            for (int y = 0; y <= x && (int)ops.size() < LIMIT; y++) {
                int v = a[x][y];
                int bx = -1, by = -1;

                if (v > a[x + 1][y]) {
                    bx = x + 1;
                    by = y;
                }
                if (v > a[x + 1][y + 1]) {
                    if (bx == -1 || a[x + 1][y + 1] < a[bx][by]) {
                        bx = x + 1;
                        by = y + 1;
                    }
                }
                if (bx != -1) {
                    if (!do_swap(x, y, bx, by)) break;
                    siftDown(bx, by);
                    changed = true;
                }
            }
        }
        if (!changed) break;
        E = calcE();
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op[0] << " " << op[1] << " " << op[2] << " " << op[3] << "\n";
    }
    return 0;
}