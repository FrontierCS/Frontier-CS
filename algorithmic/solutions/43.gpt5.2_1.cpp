#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 4, M = 96;
    vector<string> g(N, string(M, '.'));

    // Storage 2x2 at (0,0)
    g[0][0] = g[0][1] = g[1][0] = g[1][1] = 'S';

    // Box 2x2 at (0,93)
    g[0][93] = g[0][94] = g[1][93] = g[1][94] = 'B';

    // Player at (0,95)
    g[0][95] = 'P';

    cout << N << ' ' << M << '\n';
    for (int i = 0; i < N; i++) cout << g[i] << '\n';
    return 0;
}