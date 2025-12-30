#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;

    vector<string> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];

    vector<pair<int,int>> pos(26, {-1, -1});
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int idx = A[i][j] - 'A';
            if (pos[idx].first == -1) pos[idx] = {i, j};
        }
    }

    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    for (int k = 0; k < M; ++k) {
        for (char c : t[k]) {
            auto [i, j] = pos[c - 'A'];
            cout << i << ' ' << j << '\n';
        }
    }

    return 0;
}