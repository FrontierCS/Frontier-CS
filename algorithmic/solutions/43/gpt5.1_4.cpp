#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N = 2, M = 98;
    vector<string> g(N, string(M, '.'));

    // Box (2x2)
    g[0][1] = g[0][2] = g[1][1] = g[1][2] = 'B';

    // Storage location (2x2)
    g[0][96] = g[0][97] = g[1][96] = g[1][97] = 'S';

    // Player
    g[0][0] = 'P';

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}