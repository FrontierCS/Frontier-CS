#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N = 4, M = 96;
    vector<string> grid(N, string(M, '#'));

    // Create a 2-high corridor between top and bottom wall rows
    for (int r = 1; r <= 2; ++r) {
        for (int c = 1; c < M - 1; ++c) {
            grid[r][c] = '.';
        }
    }

    // Place Player
    grid[1][2] = 'P';

    // Place 2x2 Box with top-left at (1,3)
    grid[1][3] = 'B'; grid[1][4] = 'B';
    grid[2][3] = 'B'; grid[2][4] = 'B';

    // Place 2x2 Storage with top-left at (1,90)
    grid[1][90] = 'S'; grid[1][91] = 'S';
    grid[2][90] = 'S'; grid[2][91] = 'S';

    cout << N << " " << M << "\n";
    for (int r = 0; r < N; ++r) {
        cout << grid[r] << "\n";
    }
    return 0;
}