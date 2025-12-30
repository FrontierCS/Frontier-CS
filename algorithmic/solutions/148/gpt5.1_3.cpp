#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    if (!(cin >> si >> sj)) return 0;

    const int N = 50;
    vector<vector<int>> t(N, vector<int>(N));
    vector<vector<int>> p(N, vector<int>(N));

    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> t[i][j];

    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> p[i][j];

    // Output an empty path (stay at the starting cell).
    cout << '\n';

    return 0;
}