#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 30;
    vector<vector<int>> b(N);
    for (int x = 0; x < N; x++) {
        b[x].resize(x + 1);
        for (int y = 0; y <= x; y++) cin >> b[x][y];
    }

    vector<array<int,4>> ops;
    const int K_LIMIT = 10000;

    bool changed = true;
    while ((int)ops.size() < K_LIMIT && changed) {
        changed = false;
        for (int x = 0; x < N - 1; x++) {
            for (int y = 0; y <= x; y++) {
                int v = b[x][y];
                int c1 = b[x+1][y];
                int c2 = b[x+1][y+1];
                int tx = x+1, ty = y;
                int cv = c1;
                if (c2 < cv) { cv = c2; tx = x+1; ty = y+1; }
                if (v > cv) {
                    swap(b[x][y], b[tx][ty]);
                    ops.push_back({x, y, tx, ty});
                    changed = true;
                    if ((int)ops.size() >= K_LIMIT) break;
                }
            }
            if ((int)ops.size() >= K_LIMIT) break;
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}