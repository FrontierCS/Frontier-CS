#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> p(M);
    for (int i = 0; i < M; i++) cin >> p[i].first >> p[i].second;

    int ci = p[0].first, cj = p[0].second;
    for (int k = 1; k < M; k++) {
        int ti = p[k].first, tj = p[k].second;
        // Move vertically
        if (ti < ci) {
            for (int t = 0; t < ci - ti; t++) cout << "M U\n";
        } else if (ti > ci) {
            for (int t = 0; t < ti - ci; t++) cout << "M D\n";
        }
        ci = ti;
        // Move horizontally
        if (tj < cj) {
            for (int t = 0; t < cj - tj; t++) cout << "M L\n";
        } else if (tj > cj) {
            for (int t = 0; t < tj - cj; t++) cout << "M R\n";
        }
        cj = tj;
    }
    return 0;
}