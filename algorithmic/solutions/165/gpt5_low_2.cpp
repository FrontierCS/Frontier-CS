#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<string> t(M);
    for (int k = 0; k < M; ++k) cin >> t[k];

    // Precompute positions for each letter
    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            pos[A[i][j]-'A'].push_back({i,j});
        }
    }

    // Build the target sequence: concatenation of all t_k
    string seq;
    seq.reserve(5*M);
    for (int k = 0; k < M; ++k) seq += t[k];

    int ci = si, cj = sj;
    for (char c : seq) {
        int idx = c - 'A';
        // Choose nearest occurrence
        int bestd = INT_MAX;
        pair<int,int> best = pos[idx][0];
        for (auto &p : pos[idx]) {
            int d = abs(p.first - ci) + abs(p.second - cj);
            if (d < bestd) {
                bestd = d;
                best = p;
            }
        }
        cout << best.first << ' ' << best.second << '\n';
        ci = best.first; cj = best.second;
    }
    return 0;
}