#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 2, M = 98;
    vector<string> g(N, string(M, '.'));

    // Box 2x2 at columns 3-4 (0-indexed 2-3), rows 0-1
    g[0][2] = 'B'; g[0][3] = 'B';
    g[1][2] = 'B'; g[1][3] = 'B';

    // Storage 2x2 at columns 97-98 (0-indexed 96-97), rows 0-1
    g[0][96] = 'S'; g[0][97] = 'S';
    g[1][96] = 'S'; g[1][97] = 'S';

    // Player at row 0, column 2 (0-indexed 1)
    g[0][1] = 'P';

    cout << N << " " << M << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}