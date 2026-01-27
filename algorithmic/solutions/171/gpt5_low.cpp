#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int k = 0; k < M; ++k) cin >> pts[k].first >> pts[k].second;

    int r = pts[0].first, c = pts[0].second;
    // Visit targets i1..i_{M-1}
    for (int k = 1; k < M; ++k) {
        int tr = pts[k].first, tc = pts[k].second;
        // Move vertically first
        while (r > tr) { cout << "M U\n"; --r; }
        while (r < tr) { cout << "M D\n"; ++r; }
        // Then horizontally
        while (c > tc) { cout << "M L\n"; --c; }
        while (c < tc) { cout << "M R\n"; ++c; }
    }
    return 0;
}