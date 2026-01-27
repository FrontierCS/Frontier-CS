#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int k = 0; k < M; ++k) {
        cin >> pts[k].first >> pts[k].second;
    }
    int r = pts[0].first, c = pts[0].second;
    for (int k = 1; k < M; ++k) {
        int tr = pts[k].first, tc = pts[k].second;
        while (r < tr) { cout << "M D\n"; ++r; }
        while (r > tr) { cout << "M U\n"; --r; }
        while (c < tc) { cout << "M R\n"; ++c; }
        while (c > tc) { cout << "M L\n"; --c; }
    }
    return 0;
}