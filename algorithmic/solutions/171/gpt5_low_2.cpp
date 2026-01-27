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
    vector<pair<char,char>> ops;
    int ci = pts[0].first, cj = pts[0].second;
    for (int k = 1; k < M; ++k) {
        int ti = pts[k].first, tj = pts[k].second;
        while (ci < ti) { ops.emplace_back('M','D'); ci++; }
        while (ci > ti) { ops.emplace_back('M','U'); ci--; }
        while (cj < tj) { ops.emplace_back('M','R'); cj++; }
        while (cj > tj) { ops.emplace_back('M','L'); cj--; }
    }
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}