#include <bits/stdc++.h>
using namespace std;

struct Grid {
    int r, c;
    vector<string> g;
    long long black = 0, white = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    // Special minimal case: one component each
    if (b == 1 && w == 1) {
        cout << 1 << " " << 2 << "\n";
        cout << ".@" << "\n";
        return 0;
    }

    int nb = b - 1; // black dots in white block
    int nw = w - 1; // white dots in black block

    auto build_case = [&](bool sep_black) -> Grid {
        Grid res;
        int HB, HW;
        if (sep_black) {
            HB = max(1, nw);
            HW = (nb > 0 ? nb + 1 : 1);
        } else {
            HB = (nw > 0 ? nw + 1 : 1);
            HW = max(1, nb);
        }
        int H = HB + 1 + HW;
        int W = 2;
        res.r = H;
        res.c = W;
        res.g.assign(H, string(W, '.'));
        // Initialize backgrounds
        // Black block (top): rows [0, HB-1], default '@'
        for (int i = 0; i < HB; ++i) {
            for (int j = 0; j < W; ++j) res.g[i][j] = '@';
        }
        // Separator row
        int sep_row = HB;
        char sep_color = sep_black ? '@' : '.';
        for (int j = 0; j < W; ++j) res.g[sep_row][j] = sep_color;
        // White block (bottom): rows [HB+1, H-1], default '.'
        for (int i = HB + 1; i < H; ++i) {
            for (int j = 0; j < W; ++j) res.g[i][j] = '.';
        }
        // Place white dots in black block
        if (nw > 0) {
            if (sep_black) {
                for (int k = 0; k < nw; ++k) {
                    int r = k; // rows 0..HB-1, HB = nw or >= nw
                    int c = k % 2;
                    res.g[r][c] = '.';
                }
            } else {
                // must avoid last row touching white separator
                for (int k = 0; k < nw; ++k) {
                    int r = k; // HB = nw+1 so r <= HB-2
                    int c = k % 2;
                    res.g[r][c] = '.';
                }
            }
        }
        // Place black dots in white block
        if (nb > 0) {
            if (sep_black) {
                // avoid first row (adjacent to black separator)
                for (int k = 0; k < nb; ++k) {
                    int r = HB + 2 + k; // starts from second row of white block
                    int c = k % 2;
                    res.g[r][c] = '@';
                }
            } else {
                // can start immediately after separator
                for (int k = 0; k < nb; ++k) {
                    int r = HB + 1 + k;
                    int c = k % 2;
                    res.g[r][c] = '@';
                }
            }
        }
        // Count tiles
        long long B = 0, Wt = 0;
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W; ++j) {
                if (res.g[i][j] == '@') B++;
                else Wt++;
            }
        }
        res.black = B;
        res.white = Wt;
        return res;
    };

    Grid A = build_case(true);  // separator black
    Grid Bc = build_case(false); // separator white

    long long costA = 1LL * x * A.black + 1LL * y * A.white;
    long long costB = 1LL * x * Bc.black + 1LL * y * Bc.white;

    Grid best = (costA <= costB ? A : Bc);

    cout << best.r << " " << best.c << "\n";
    for (int i = 0; i < best.r; ++i) {
        cout << best.g[i] << "\n";
    }
    return 0;
}