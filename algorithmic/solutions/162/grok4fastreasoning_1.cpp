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
    auto sift_down = [&](int px, int py) {
        while (true) {
            int self_val = grid[px][py];
            int min_val = self_val;
            int cx = px, cy = py;
            bool has_left = (px + 1 < 30);
            bool has_right = has_left && (py + 1 <= px + 1);
            if (has_left) {
                int lval = grid[px + 1][py];
                if (lval < min_val) {
                    min_val = lval;
                    cx = px + 1;
                    cy = py;
                }
            }
            if (has_right) {
                int rval = grid[px + 1][py + 1];
                if (rval < min_val) {
                    min_val = rval;
                    cx = px + 1;
                    cy = py + 1;
                }
            }
            if (cx == px && cy == py) break;
            swaps.emplace_back(px, py, cx, cy);
            swap(grid[px][py], grid[cx][cy]);
            px = cx;
            py = cy;
        }
    };
    for (int x = 28; x >= 0; x--) {
        for (int y = 0; y <= x; y++) {
            sift_down(x, y);
        }
    }
    cout << swaps.size() << endl;
    for (auto [x1, y1, x2, y2] : swaps) {
        cout << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    }
    return 0;
}