#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int L = N * M;

    vector<int> color(L + 1);
    for (int i = 1; i <= L; ++i) {
        cin >> color[i];
    }

    vector<vector<int>> pos(N + 1);
    for (int i = 1; i <= L; ++i) {
        int c = color[i];
        if (c >= 1 && c <= N)
            pos[c].push_back(i);
    }

    // Assume input is valid: each color appears exactly M times
    for (int j = 0; j < M; ++j) {
        cout << '!';
        for (int c = 1; c <= N; ++c) {
            cout << ' ' << pos[c][j];
        }
        cout << '\n';
    }
    return 0;
}