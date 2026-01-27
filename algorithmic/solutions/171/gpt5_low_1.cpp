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
    vector<pair<char,char>> out;
    auto emit = [&](char dir){
        out.emplace_back('M', dir);
    };
    for (int k = 1; k < M; ++k) {
        int ti = pts[k].first, tj = pts[k].second;
        while (ci < ti) { emit('D'); ci++; }
        while (ci > ti) { emit('U'); ci--; }
        while (cj < tj) { emit('R'); cj++; }
        while (cj > tj) { emit('L'); cj--; }
    }
    for (auto &p : out) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}