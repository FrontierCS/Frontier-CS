#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    vector<string> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];

    vector<string> t(M);
    for (int k = 0; k < M; k++) cin >> t[k];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            pos[A[i][j] - 'A'].push_back({i, j});
        }
    }

    int ci = si, cj = sj;
    vector<pair<int,int>> ans;
    ans.reserve(M * 5);

    for (int k = 0; k < M; k++) {
        for (char ch : t[k]) {
            auto &v = pos[ch - 'A'];
            int bestIdx = 0;
            int bestDist = INT_MAX;
            for (int idx = 0; idx < (int)v.size(); idx++) {
                int di = abs(v[idx].first - ci) + abs(v[idx].second - cj);
                if (di < bestDist) {
                    bestDist = di;
                    bestIdx = idx;
                }
            }
            ci = v[bestIdx].first;
            cj = v[bestIdx].second;
            ans.push_back({ci, cj});
        }
    }

    for (auto [i, j] : ans) {
        cout << i << ' ' << j << '\n';
    }
    return 0;
}