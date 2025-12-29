#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 2, M = 98;
    vector<string> grid(N, string(M, '.'));

    // Place storage (S) at the far right (2x2)
    for (int r = 0; r < 2; ++r) {
        grid[r][M-2] = 'S';
        grid[r][M-1] = 'S';
    }

    // Place box (B) near the left (2x2)
    grid[0][1] = 'B';
    grid[0][2] = 'B';
    grid[1][1] = 'B';
    grid[1][2] = 'B';

    // Place player (P) to the left of the box
    grid[0][0] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) cout << grid[i] << "\n";
    return 0;
}