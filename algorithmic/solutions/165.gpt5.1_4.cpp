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
    for (int i = 0; i < N; i++) cin >> A[i];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            pos[A[i][j] - 'A'].push_back({i, j});
        }
    }

    string total;
    int maxWords = min(M, 5000 / 5);
    total.reserve(maxWords * 5);

    for (int k = 0; k < M; k++) {
        string t;
        cin >> t;
        if (k < maxWords) total += t;
    }

    vector<pair<int,int>> ops;
    ops.reserve(total.size());

    int ci = si, cj = sj;
    for (char ch : total) {
        auto &vec = pos[ch - 'A'];
        int best_i = vec[0].first, best_j = vec[0].second;
        int bestd = abs(best_i - ci) + abs(best_j - cj);
        for (auto &p : vec) {
            int i = p.first, j = p.second;
            int d = abs(i - ci) + abs(j - cj);
            if (d < bestd) {
                bestd = d;
                best_i = i;
                best_j = j;
            }
        }
        ci = best_i;
        cj = best_j;
        ops.push_back({ci, cj});
    }

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}