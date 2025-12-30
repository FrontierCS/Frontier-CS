#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<vector<int>> grid(30);
    for (int x = 0; x < 30; x++) {
        grid[x].resize(x + 1);
        for (int y = 0; y <= x; y++) {
            cin >> grid[x][y];
        }
    }
    vector<tuple<int, int, int, int>> swaps;
    auto siftdown = [&](auto&& self, int cx, int cy) -> void {
        while (true) {
            int val = grid[cx][cy];
            int lx = cx + 1, ly = cy;
            int rx = cx + 1, ry = cy + 1;
            int sx = cx, sy = cy;
            int smallest = val;
            if (lx < 30) {
                int lval = grid[lx][ly];
                if (lval < smallest) {
                    smallest = lval;
                    sx = lx;
                    sy = ly;
                }
                if (ry <= rx) {
                    int rval = grid[rx][ry];
                    if (rval < smallest) {
                        smallest = rval;
                        sx = rx;
                        sy = ry;
                    }
                }
            }
            if (sx == cx && sy == cy) break;
            swap(grid[cx][cy], grid[sx][sy]);
            swaps.emplace_back(cx, cy, sx, sy);
            cx = sx;
            cy = sy;
        }
    };
    for (int ix = 28; ix >= 0; ix--) {
        for (int iy = 0; iy <= ix; iy++) {
            siftdown(siftdown, ix, iy);
        }
    }
    cout << swaps.size() << endl;
    for (auto [x1, y1, x2, y2] : swaps) {
        cout << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    }
}