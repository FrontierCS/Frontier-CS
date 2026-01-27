#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 2, M = 98;
    vector<string> g(N, string(M, '.'));

    // Place box (2x2) at columns 1 and 2, rows 0 and 1
    for (int r = 0; r < 2; ++r)
        for (int c = 1; c <= 2; ++c)
            g[r][c] = 'B';

    // Place storage (2x2) at the far right
    int sL = M - 2;
    for (int r = 0; r < 2; ++r)
        for (int c = sL; c < M; ++c)
            g[r][c] = 'S';

    // Place player to the left of the box
    g[0][0] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}