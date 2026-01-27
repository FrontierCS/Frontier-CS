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

    const int Klimit = 10000;
    struct Op { int x1,y1,x2,y2; };
    vector<Op> ops;
    ops.reserve(Klimit);

    bool changed = true;
    while (changed && (int)ops.size() < Klimit) {
        changed = false;
        for (int x = 0; x < N - 1 && (int)ops.size() < Klimit; ++x) {
            for (int y = 0; y <= x && (int)ops.size() < Klimit; ++y) {
                int p = b[x][y];
                int c1 = b[x+1][y];
                int c2 = b[x+1][y+1];
                if (p > c1 || p > c2) {
                    if (c1 <= c2) {
                        swap(b[x][y], b[x+1][y]);
                        ops.push_back({x, y, x+1, y});
                    } else {
                        swap(b[x][y], b[x+1][y+1]);
                        ops.push_back({x, y, x+1, y+1});
                    }
                    changed = true;
                }
            }
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' ' << op.x2 << ' ' << op.y2 << '\n';
    }
    return 0;
}