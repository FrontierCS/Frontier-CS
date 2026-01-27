#include <bits/stdc++.h>
using namespace std;

static inline int ceil_div_int(int a, int b) {
    return (a + b - 1) / b;
}

struct Best {
    long long cost = (1LL << 62);
    long long area = (1LL << 62);
    int type = -1; // 0 = vertical split, 1 = horizontal split
    int p1 = 0, p2 = 0, p3 = 0; // vertical: hb, hw, c; horizontal: r, cb, cw
};

static inline void upd(Best& best, long long cost, long long area, int type, int p1, int p2, int p3, int r, int c) {
    if (r < 1 || c < 1 || r > 100000 || c > 100000) return;
    if (area > 100000) return;
    if (cost < best.cost || (cost == best.cost && (area < best.area))) {
        best.cost = cost;
        best.area = area;
        best.type = type;
        best.p1 = p1;
        best.p2 = p2;
        best.p3 = p3;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    cin >> b >> w >> x >> y;

    int minDim = (b == 1 && w == 1) ? 1 : 2;

    Best best;

    // Vertical split: top black (hb rows), bottom white (hw rows), common width c.
    for (int c = minDim; c <= 100000; ++c) {
        int posPerRow = (c + 1) / 2; // columns 0,2,4,...
        int hb = (w == 1) ? 1 : 2 * ceil_div_int(w - 1, posPerRow); // even
        int hw = (b == 1) ? 1 : 2 * ceil_div_int(b - 1, posPerRow); // even
        long long r = 1LL * hb + hw;
        long long area = r * c;
        if (area > 100000 || r > 100000) continue;

        long long B = 1LL * hb * c - (w - 1) + (b - 1);
        long long W = area - B;
        long long cost = 1LL * x * B + 1LL * y * W;

        upd(best, cost, area, 0, hb, hw, c, (int)r, c);
    }

    // Horizontal split: left black (cb cols), right white (cw cols), common height r.
    for (int r = minDim; r <= 100000; ++r) {
        int posPerCol = (r + 1) / 2; // rows 0,2,4,...
        int cb = (w == 1) ? 1 : 2 * ceil_div_int(w - 1, posPerCol); // even
        int cw = (b == 1) ? 1 : 2 * ceil_div_int(b - 1, posPerCol); // even
        long long c = 1LL * cb + cw;
        long long area = 1LL * r * c;
        if (area > 100000 || c > 100000) continue;

        long long B = 1LL * r * cb - (w - 1) + (b - 1);
        long long W = area - B;
        long long cost = 1LL * x * B + 1LL * y * W;

        upd(best, cost, area, 1, r, cb, cw, r, (int)c);
    }

    // Special case: b=w=1 could be 1x2 or 2x1; ensure at least one candidate.
    if (best.type == -1) {
        // Fallback to a simple 2x2 robust construction.
        int r = 2, c = 2;
        vector<string> g = {"@.", ".@"};
        cout << r << " " << c << "\n";
        for (auto &row : g) cout << row << "\n";
        return 0;
    }

    vector<string> grid;

    if (best.type == 0) {
        int hb = best.p1, hw = best.p2, c = best.p3;
        int r = hb + hw;
        grid.assign(r, string(c, '.'));
        for (int i = 0; i < hb; ++i) grid[i].assign(c, '@');
        for (int i = hb; i < r; ++i) grid[i].assign(c, '.');

        int needW = w - 1;
        for (int i = 0; i < hb - 1 && needW > 0; i += 2) {
            for (int j = 0; j < c && needW > 0; j += 2) {
                grid[i][j] = '.';
                --needW;
            }
        }

        int needB = b - 1;
        for (int i = hb + 1; i < r && needB > 0; i += 2) {
            for (int j = 0; j < c && needB > 0; j += 2) {
                grid[i][j] = '@';
                --needB;
            }
        }

        cout << r << " " << c << "\n";
        for (auto &row : grid) cout << row << "\n";
    } else {
        int r = best.p1, cb = best.p2, cw = best.p3;
        int c = cb + cw;
        grid.assign(r, string(c, '.'));
        for (int i = 0; i < r; ++i) {
            for (int j = 0; j < cb; ++j) grid[i][j] = '@';
            for (int j = cb; j < c; ++j) grid[i][j] = '.';
        }

        int needW = w - 1;
        for (int i = 0; i < r && needW > 0; i += 2) {
            for (int j = 0; j < cb - 1 && needW > 0; j += 2) { // exclude boundary col cb-1
                grid[i][j] = '.';
                --needW;
            }
        }

        int needB = b - 1;
        for (int i = 0; i < r && needB > 0; i += 2) {
            for (int j = cb + 1; j < c && needB > 0; j += 2) { // exclude boundary col cb
                grid[i][j] = '@';
                --needB;
            }
        }

        cout << r << " " << c << "\n";
        for (auto &row : grid) cout << row << "\n";
    }

    return 0;
}