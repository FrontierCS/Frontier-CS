#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = grid[i][j];
            pos[c - 'A'].push_back({i, j});
        }
    }

    int ci = si, cj = sj;
    int ops = 0;

    for (int k = 0; k < M; ++k) {
        const string &pat = t[k];
        for (char ch : pat) {
            const auto &vec = pos[ch - 'A'];
            int bi = vec[0].first, bj = vec[0].second;
            int best = abs(bi - ci) + abs(bj - cj);
            for (const auto &p : vec) {
                int d = abs(p.first - ci) + abs(p.second - cj);
                if (d < best) {
                    best = d;
                    bi = p.first;
                    bj = p.second;
                }
            }
            cout << bi << ' ' << bj << '\n';
            ci = bi;
            cj = bj;
            if (++ops >= 5000) return 0;
        }
    }

    return 0;
}