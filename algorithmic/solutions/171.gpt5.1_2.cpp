#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<int> r(M), c(M);
    for (int i = 0; i < M; i++) {
        cin >> r[i] >> c[i];
    }

    vector<pair<char,char>> cmds;

    for (int k = 0; k < M - 1; k++) {
        int r0 = r[k], c0 = c[k];
        int r1 = r[k + 1], c1 = c[k + 1];

        if (r1 > r0) {
            for (int t = 0; t < r1 - r0; t++) cmds.push_back({'M', 'D'});
        } else {
            for (int t = 0; t < r0 - r1; t++) cmds.push_back({'M', 'U'});
        }

        if (c1 > c0) {
            for (int t = 0; t < c1 - c0; t++) cmds.push_back({'M', 'R'});
        } else {
            for (int t = 0; t < c0 - c1; t++) cmds.push_back({'M', 'L'});
        }
    }

    for (auto &p : cmds) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}