#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 50, M = 50;
    vector<string> g(N, string(M, '.'));

    // Borders
    for (int i = 0; i < N; ++i) {
        g[i][0] = '#';
        g[i][M-1] = '#';
    }
    for (int j = 0; j < M; ++j) {
        g[0][j] = '#';
        g[N-1][j] = '#';
    }

    // Box (2x2) at (2,2)-(3,3)
    int rB = 2, cB = 2;
    g[rB][cB] = 'B';
    g[rB][cB+1] = 'B';
    g[rB+1][cB] = 'B';
    g[rB+1][cB+1] = 'B';

    // Storage (2x2) near bottom-right
    int rS = N - 3, cS = M - 3;
    g[rS][cS] = 'S';
    g[rS][cS+1] = 'S';
    g[rS+1][cS] = 'S';
    g[rS+1][cS+1] = 'S';

    // Player left of the box
    g[rB][cB-1] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}