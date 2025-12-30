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
    for (int i = 0; i < N; i++) {
        cin >> A[i];
    }

    vector<string> t(M);
    for (int i = 0; i < M; i++) cin >> t[i];

    // Precompute positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            char c = A[i][j];
            pos[c - 'A'].push_back({i, j});
        }
    }

    int ci = si, cj = sj;

    // Type each t_k sequentially, greedily choosing nearest key for each char
    for (int k = 0; k < M; k++) {
        for (char c : t[k]) {
            int idx = c - 'A';
            const auto &v = pos[idx];
            int best_i = v[0].first;
            int best_j = v[0].second;
            int best_d = abs(best_i - ci) + abs(best_j - cj);
            for (const auto &p : v) {
                int d = abs(p.first - ci) + abs(p.second - cj);
                if (d < best_d) {
                    best_d = d;
                    best_i = p.first;
                    best_j = p.second;
                }
            }
            cout << best_i << ' ' << best_j << '\n';
            ci = best_i;
            cj = best_j;
        }
    }

    return 0;
}