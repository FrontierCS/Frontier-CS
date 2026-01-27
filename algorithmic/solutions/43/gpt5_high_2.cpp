#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 2, M = 98;
    cout << N << " " << M << "\n";
    vector<string> grid(N, string(M, '.'));

    // Place player
    grid[0][0] = 'P';

    // Place 2x2 box 'B' with top-left at (0,1)
    grid[0][1] = 'B'; grid[0][2] = 'B';
    grid[1][1] = 'B'; grid[1][2] = 'B';

    // Place 2x2 storage 'S' with top-left at (0,96)
    grid[0][96] = 'S'; grid[0][97] = 'S';
    grid[1][96] = 'S'; grid[1][97] = 'S';

    for (int i = 0; i < N; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}