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
    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    // Build target string S by simple concatenation of all t_k
    string S;
    S.reserve(5 * M);
    for (int k = 0; k < M; ++k) S += t[k];

    // Precompute positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            pos[A[i][j] - 'A'].emplace_back(i, j);
        }
    }

    // Greedy: for each character, move to nearest occurrence
    int ci = si, cj = sj;
    vector<pair<int,int>> ops;
    ops.reserve(S.size());
    for (char ch : S) {
        int idx = ch - 'A';
        const auto &vec = pos[idx];
        int bestd = INT_MAX;
        pair<int,int> bestp = vec[0];
        for (const auto &p : vec) {
            int d = abs(p.first - ci) + abs(p.second - cj);
            if (d < bestd) {
                bestd = d;
                bestp = p;
            }
        }
        ops.push_back(bestp);
        ci = bestp.first;
        cj = bestp.second;
    }

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}