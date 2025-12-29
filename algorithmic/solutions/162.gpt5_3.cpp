#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 30;
    vector<vector<int>> a(N);
    for (int x = 0; x < N; x++) {
        a[x].resize(x + 1);
        for (int y = 0; y <= x; y++) {
            cin >> a[x][y];
        }
    }

    vector<pair<int,int>> pos(465);
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            pos[a[x][y]] = {x, y};
        }
    }

    struct Move { int x1,y1,x2,y2; };
    vector<Move> ops;
    ops.reserve(5000);

    auto doSwap = [&](int x1, int y1, int x2, int y2){
        int v1 = a[x1][y1];
        int v2 = a[x2][y2];
        swap(a[x1][y1], a[x2][y2]);
        pos[v1] = {x2, y2};
        pos[v2] = {x1, y1};
        ops.push_back({x1,y1,x2,y2});
    };

    for (int x = 0; x <= N-2; x++) {
        for (int y = 0; y <= x; y++) {
            int bestVal = INT_MAX;
            int bx = -1, by = -1;
            for (int i = x; i < N; i++) {
                int start = y;
                int end = y + (i - x);
                for (int j = start; j <= end; j++) {
                    int val = a[i][j];
                    if (val < bestVal) {
                        bestVal = val;
                        bx = i; by = j;
                    }
                }
            }
            while (bx > x) {
                if (by > y) {
                    doSwap(bx-1, by-1, bx, by);
                    bx--; by--;
                } else {
                    doSwap(bx-1, by, bx, by);
                    bx--;
                }
            }
        }
    }

    cout << ops.size() << '\n';
    for (auto &m : ops) {
        cout << m.x1 << ' ' << m.y1 << ' ' << m.x2 << ' ' << m.y2 << '\n';
    }
    return 0;
}