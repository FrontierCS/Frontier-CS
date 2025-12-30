#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; ++k) cin >> I[k] >> J[k];

    vector<pair<char, char>> actions;

    for (int k = 1; k < M; ++k) {
        int ci = I[k-1], cj = J[k-1];
        int ti = I[k],   tj = J[k];

        int di = ti - ci;
        int dj = tj - cj;

        // Vertical moves
        if (di < 0) {
            for (int t = 0; t < -di; ++t) actions.push_back({'M','U'});
        } else if (di > 0) {
            for (int t = 0; t < di; ++t) actions.push_back({'M','D'});
        }

        // Horizontal moves
        if (dj < 0) {
            for (int t = 0; t < -dj; ++t) actions.push_back({'M','L'});
        } else if (dj > 0) {
            for (int t = 0; t < dj; ++t) actions.push_back({'M','R'});
        }
    }

    for (auto &p : actions) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}