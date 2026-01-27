#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    // Characters for colors
    char BLACK = '@';
    char WHITE = '.';

    // Decide cheap and expensive colors
    bool blackCheap = (x <= y);
    char C_char = blackCheap ? BLACK : WHITE; // cheap color
    char E_char = blackCheap ? WHITE : BLACK; // expensive color

    int cCount = blackCheap ? b : w; // number of cheap color components needed
    int eCount = blackCheap ? w : b; // number of expensive color components needed

    vector<string> grid;
    int R, W;

    if (cCount == 1) {
        int nE = eCount;
        W = max(1, 2 * nE - 1);
        R = 2;

        grid.assign(R, string(W, C_char));
        for (int i = 0; i < nE; ++i) {
            int col = 2 * i;
            grid[1][col] = E_char;
        }
    } else {
        int nE = eCount - 1;
        int nC = cCount - 1;

        W = max(1, max(2 * nE - 1, 2 * nC - 1));
        if (nE > 0) W = max(W, 2); // ensure connectivity of the cheap sea across an expensive island row

        R = 5;
        grid.resize(R);
        // Rows 0,1,2 are cheap color by default
        grid[0] = string(W, C_char);
        grid[1] = string(W, C_char);
        grid[2] = string(W, C_char);
        // Rows 3,4 are expensive color by default
        grid[3] = string(W, E_char);
        grid[4] = string(W, E_char);

        // Place expensive islands in row 1
        for (int i = 0; i < nE; ++i) {
            int col = 2 * i;
            grid[1][col] = E_char;
        }

        // Place cheap islands in row 4
        for (int i = 0; i < nC; ++i) {
            int col = 2 * i;
            grid[4][col] = C_char;
        }
    }

    cout << grid.size() << " " << grid[0].size() << "\n";
    for (auto &row : grid) {
        cout << row << "\n";
    }

    return 0;
}