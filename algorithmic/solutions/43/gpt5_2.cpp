#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 98, M = 2;
    vector<string> grid(N, string(M, '.'));

    // Place box (2x2) at top-left corner starting at (1, 0)
    int rB = 1, cB = 0;
    for (int dr = 0; dr < 2; ++dr)
        for (int dc = 0; dc < 2; ++dc)
            grid[rB + dr][cB + dc] = 'B';

    // Place storage (2x2) at bottom starting at (96, 0)
    int rS = 96, cS = 0;
    for (int dr = 0; dr < 2; ++dr)
        for (int dc = 0; dc < 2; ++dc)
            grid[rS + dr][cS + dc] = 'S';

    // Place player above the box
    grid[0][0] = 'P';

    cout << N << " " << M << "\n";
    for (const auto &row : grid) {
        cout << row << "\n";
    }
    return 0;
}