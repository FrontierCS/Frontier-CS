#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> p(M);
    for (int k = 0; k < M; ++k) cin >> p[k].first >> p[k].second;

    int r = p[0].first, c = p[0].second;
    for (int k = 1; k < M; ++k) {
        int nr = p[k].first, nc = p[k].second;
        while (r < nr) { cout << "M D\n"; ++r; }
        while (r > nr) { cout << "M U\n"; --r; }
        while (c < nc) { cout << "M R\n"; ++c; }
        while (c > nc) { cout << "M L\n"; --c; }
    }
    return 0;
}