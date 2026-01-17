#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int L = N * M;

    vector<vector<int>> pos(N + 1);
    for (int i = 1; i <= L; ++i) {
        int c;
        if (!(cin >> c)) return 0; // Expecting color of dango i
        if (c < 1 || c > N) return 0;
        pos[c].push_back(i);
    }

    // Assume each color appears exactly M times
    for (int s = 0; s < M; ++s) {
        cout << "!";
        for (int color = 1; color <= N; ++color) {
            if ((int)pos[color].size() <= s) return 0; // invalid input
            cout << " " << pos[color][s];
        }
        cout << "\n";
    }

    return 0;
}