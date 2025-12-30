#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    array<vector<pair<int,int>>, 26> pos;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            char c = grid[i][j];
            pos[c - 'A'].push_back({i, j});
        }
    }

    vector<string> t(M);
    for (int i = 0; i < M; i++) cin >> t[i];

    string S;
    S.reserve(5 * M);
    for (int i = 0; i < M; i++) S += t[i];

    int ci = si, cj = sj;
    for (char ch : S) {
        const auto &v = pos[ch - 'A'];
        int bestIdx = 0;
        int bestDist = INT_MAX;
        for (int k = 0; k < (int)v.size(); k++) {
            int di = abs(v[k].first - ci) + abs(v[k].second - cj);
            if (di < bestDist) {
                bestDist = di;
                bestIdx = k;
            }
        }
        ci = v[bestIdx].first;
        cj = v[bestIdx].second;
        cout << ci << " " << cj << "\n";
    }

    return 0;
}