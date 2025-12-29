#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<pair<int,int>> p(M);
    for (int k = 0; k < M; k++) cin >> p[k].first >> p[k].second;

    vector<pair<char,char>> ans;
    auto add_move = [&](char dir) {
        ans.push_back({'M', dir});
    };

    int ci = p[0].first, cj = p[0].second;
    for (int k = 1; k < M; k++) {
        int ti = p[k].first, tj = p[k].second;

        while (ci < ti) { add_move('D'); ci++; }
        while (ci > ti) { add_move('U'); ci--; }
        while (cj < tj) { add_move('R'); cj++; }
        while (cj > tj) { add_move('L'); cj--; }
    }

    int limit = 2 * N * M;
    if ((int)ans.size() > limit) {
        // Fallback: should never happen with N=20,M=40
        ans.resize(limit);
    }

    for (auto [a, d] : ans) {
        cout << a << ' ' << d << '\n';
    }
    return 0;
}