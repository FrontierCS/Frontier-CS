#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 5, M = 8;
    vector<string> grid(N, string(M, '.'));

    // Place 2x2 box 'B' at rows 2-3, cols 2-3 (0-based)
    for (int r = 2; r <= 3; ++r)
        for (int c = 2; c <= 3; ++c)
            grid[r][c] = 'B';

    // Place 2x2 storage 'S' at rows 2-3, cols 5-6 (0-based)
    for (int r = 2; r <= 3; ++r)
        for (int c = 5; c <= 6; ++c)
            grid[r][c] = 'S';

    // Place player 'P' left of the box
    grid[2][1] = 'P';

    cout << N << " " << M << "\n";
    for (auto &row : grid) cout << row << "\n";
    return 0;
}