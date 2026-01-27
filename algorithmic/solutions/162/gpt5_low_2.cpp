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

    struct Op { int x1,y1,x2,y2; };
    vector<Op> ops;
    const int KMAX = 10000;

    auto swap_op = [&](int x1,int y1,int x2,int y2){
        if ((int)ops.size() >= KMAX) return false;
        swap(b[x1][y1], b[x2][y2]);
        ops.push_back({x1,y1,x2,y2});
        return true;
    };

    bool changed = true;
    while (changed && (int)ops.size() < KMAX) {
        changed = false;
        for (int x = 0; x <= N-2; x++) {
            for (int y = 0; y <= x; y++) {
                if (b[x][y] > b[x+1][y]) {
                    if (!swap_op(x, y, x+1, y)) break;
                    changed = true;
                }
                if ((int)ops.size() >= KMAX) break;
                if (b[x][y] > b[x+1][y+1]) {
                    if (!swap_op(x, y, x+1, y+1)) break;
                    changed = true;
                }
            }
            if ((int)ops.size() >= KMAX) break;
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' ' << op.x2 << ' ' << op.y2 << '\n';
    }
    return 0;
}