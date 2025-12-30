#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 50, M = 50;
    vector<string> grid(N, string(M, '.'));

    // Place box (2x2) at (2,2)-(3,3)
    int br = 2, bc = 2;
    for (int i = 0; i < 2; ++i)
        for (int j = 0; j < 2; ++j)
            grid[br + i][bc + j] = 'B';

    // Place storage (2x2) near bottom-right
    int sr = N - 4, sc = M - 4;
    for (int i = 0; i < 2; ++i)
        for (int j = 0; j < 2; ++j)
            grid[sr + i][sc + j] = 'S';

    // Place player
    grid[0][0] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}