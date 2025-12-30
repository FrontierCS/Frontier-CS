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

    int ops = 0;
    for (int k = 0; k < M && ops < 5000; ++k) {
        for (char c : t[k]) {
            if (ops >= 5000) break;
            auto p = pos[c - 'A'];
            int i = p.first, j = p.second;
            if (i == -1) { // should not happen due to guarantees
                i = si;
                j = sj;
            }
            cout << i << ' ' << j << '\n';
            ++ops;
        }
    }

    return 0;
}