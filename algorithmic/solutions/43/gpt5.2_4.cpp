#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 4, M = 96; // N + M = 100
    vector<string> g(N, string(M, '.'));

    for (int j = 0; j < M; j++) g[0][j] = g[N-1][j] = '#';
    for (int i = 1; i < N-1; i++) g[i][0] = g[i][M-1] = '#';

    // Player
    g[1][2] = 'P';

    // Box 2x2 at (1,3)
    for (int i = 1; i <= 2; i++)
        for (int j = 3; j <= 4; j++)
            g[i][j] = 'B';

    // Storage 2x2 at (1,92)
    for (int i = 1; i <= 2; i++)
        for (int j = 92; j <= 93; j++)
            g[i][j] = 'S';

    cout << N << " " << M << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}