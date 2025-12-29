#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> P(M);
    for (int k = 0; k < M; ++k) {
        cin >> P[k].first >> P[k].second;
    }
    
    int r = P[0].first, c = P[0].second;
    for (int k = 1; k < M; ++k) {
        int tr = P[k].first, tc = P[k].second;
        if (tr > r) {
            for (int i = 0; i < tr - r; ++i) cout << "M D\n";
        } else {
            for (int i = 0; i < r - tr; ++i) cout << "M U\n";
        }
        r = tr;
        if (tc > c) {
            for (int i = 0; i < tc - c; ++i) cout << "M R\n";
        } else {
            for (int i = 0; i < c - tc; ++i) cout << "M L\n";
        }
        c = tc;
    }
    return 0;
}