#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    vector<vector<int>> a(N, vector<int>(N, 0));
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            if (!(cin >> a[x][y])) return 0;
        }
    }

    const int MAX_OP = 10000;
    vector<array<int,4>> ops;
    ops.reserve(MAX_OP);

    bool changed = true;
    while (changed && (int)ops.size() < MAX_OP) {
        changed = false;
        bool limit = false;
        for (int x = N - 2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                if ((int)ops.size() >= MAX_OP) { limit = true; break; }

                int px = x, py = y;
                int p = a[px][py];
                int cx1 = px + 1, cy1 = py;
                int cx2 = px + 1, cy2 = py + 1;

                int v1 = a[cx1][cy1];
                int v2 = a[cx2][cy2];

                int bestx, besty, bestv;
                if (v1 <= v2) {
                    bestx = cx1; besty = cy1; bestv = v1;
                } else {
                    bestx = cx2; besty = cy2; bestv = v2;
                }

                if (p > bestv) {
                    swap(a[px][py], a[bestx][besty]);
                    ops.push_back({px, py, bestx, besty});
                    changed = true;
                }
            }
            if (limit) break;
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }

    return 0;
}