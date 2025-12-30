#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 50, M = 50;
    vector<string> g(N, string(M, '.'));

    // Player
    g[0][2] = 'P';

    // Box (2x2) at (2,2) in 1-based indexing -> (1,1) in 0-based
    for (int i = 1; i <= 2; ++i) {
        for (int j = 1; j <= 2; ++j) {
            g[i][j] = 'B';
        }
    }

    // Storage (2x2) at bottom-right
    for (int i = 48; i <= 49; ++i) {
        for (int j = 48; j <= 49; ++j) {
            g[i][j] = 'S';
        }
    }

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}