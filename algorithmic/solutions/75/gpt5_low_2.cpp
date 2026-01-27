#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    // Special case: 1D optimal if |b-w| <= 1
    if (abs(b - w) <= 1) {
        int r = 1, c = b + w;
        cout << r << " " << c << "\n";
        bool startBlack = (b >= w);
        int cb = 0, cw = 0;
        for (int i = 0; i < c; ++i) {
            bool putBlack = ( (i % 2 == 0) ? startBlack : !startBlack );
            if (putBlack) {
                if (cb < b) {
                    cout << '@';
                    cb++;
                } else {
                    cout << '.';
                    cw++;
                }
            } else {
                if (cw < w) {
                    cout << '.';
                    cw++;
                } else {
                    cout << '@';
                    cb++;
                }
            }
        }
        cout << "\n";
        return 0;
    }

    // General construction with 5 rows:
    // Upper 2 rows: white base with b black islands on row 0 at even columns.
    // Row 2: black separator (with one white cell to connect a white island).
    // Lower 2 rows: black base with w white islands on row 3 at even columns.
    int W = max(2*b - 1, 2*w - 1);
    int R = 5;
    vector<string> g(R, string(W, '@'));

    // Initialize:
    // Rows 0-1 white
    for (int c = 0; c < W; ++c) g[0][c] = g[1][c] = '.';
    // Row 2 black by default (already '@')
    // Rows 3-4 black by default (already '@')

    // Place black islands in upper section (row 0 at even columns)
    for (int i = 0; i < b; ++i) {
        int col = 2*i;
        g[0][col] = '@';
        // ensure separator columns (odd) in upper remain white
        if (col + 1 < W) {
            g[0][col+1] = '.';
            g[1][col+1] = '.';
        }
    }

    // Place white islands in lower section (row 3 at even columns)
    for (int i = 0; i < w; ++i) {
        int col = 2*i;
        g[3][col] = '.';
        // separators odd columns remain black (already '@')
    }

    // Connect one black island to black base: set row 1 at a black island column to '@'
    int k1;
    if (b == 1) {
        // Use column 0 (only island) for black connection
        k1 = 0;
    } else {
        // rightmost black island column
        k1 = 2*(b-1);
    }
    g[1][k1] = '@';

    // Connect one white island to upper white base through row 2 white cell at a (different) island column
    int k2;
    if (b == 1) {
        // Ensure different column from k1=0; need w>=2 (since |b-w|>1 implies w>=3 actually when b=1)
        k2 = (w >= 2 ? 2 : 0);
    } else {
        // choose the leftmost white island at column 0
        k2 = 0;
        if (k2 == k1) {
            // if by chance equal (when k1==0), shift to next available white island column if exists
            if (w >= 2) k2 = 2;
            else {
                // fallback: increase width to allow separate column (rare, e.g., b>1,w=1 and k1==0)
                // Expand grid by 2 columns to the right
                int oldW = W;
                W += 2;
                for (int r = 0; r < R; ++r) g[r].resize(W, '@');
                g[0].replace(oldW, 2, "..");
                g[1].replace(oldW, 2, "..");
                // row2 '@@' already
                // rows3-4 '@@' already
                k2 = oldW; // new even column
                g[3][k2] = '.';
            }
        }
    }
    // Ensure k2 within bounds and corresponds to a white island column
    if (k2 >= W) {
        // Shouldn't happen due to above handling, but guard
        k2 = (w >= 1 ? 2*(w-1) : 0);
        if (k2 >= W) k2 = 0;
    }
    // Make separator at k2 white to connect that white island to upper white base
    g[2][k2] = '.';

    // Output
    cout << R << " " << W << "\n";
    for (int r = 0; r < R; ++r) {
        cout << g[r] << "\n";
    }
    return 0;
}