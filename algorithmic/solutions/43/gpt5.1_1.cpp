#include <bits/stdc++.h>
using namespace std;

int main() {
    const int N = 4;
    const int M = 96;
    vector<string> g(N, string(M, '.'));

    // Top and bottom walls
    for (int j = 0; j < M; ++j) {
        g[0][j] = '#';
        g[3][j] = '#';
    }

    // Side walls in middle rows
    for (int i = 1; i <= 2; ++i) {
        g[i][0] = '#';
        g[i][1] = '#';
        g[i][M - 1] = '#';
    }

    // Storage 2x2 at (rows 1-2, cols 2-3)
    for (int i = 1; i <= 2; ++i)
        for (int j = 2; j <= 3; ++j)
            g[i][j] = 'S';

    // Box 2x2 at (rows 1-2, cols 92-93)
    for (int i = 1; i <= 2; ++i)
        for (int j = 92; j <= 93; ++j)
            g[i][j] = 'B';

    // Player at row 2, col 94
    g[2][94] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}