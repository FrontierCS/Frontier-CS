#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int k = 0; k < M; ++k) cin >> pts[k].first >> pts[k].second;

    int ci = pts[0].first, cj = pts[0].second;
    for (int k = 1; k < M; ++k) {
        int ti = pts[k].first, tj = pts[k].second;
        while (ci < ti) { cout << "M D\n"; ++ci; }
        while (ci > ti) { cout << "M U\n"; --ci; }
        while (cj < tj) { cout << "M R\n"; ++cj; }
        while (cj > tj) { cout << "M L\n"; --cj; }
    }
    return 0;
}