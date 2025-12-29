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

    vector<pair<char,char>> out;
    int ci = pts[0].first, cj = pts[0].second;

    for (int k = 1; k < M; ++k) {
        int ti = pts[k].first, tj = pts[k].second;
        int di = ti - ci;
        int dj = tj - cj;

        if (di < 0) {
            for (int t = 0; t < -di; ++t) out.push_back({'M','U'});
        } else if (di > 0) {
            for (int t = 0; t < di; ++t) out.push_back({'M','D'});
        }

        if (dj < 0) {
            for (int t = 0; t < -dj; ++t) out.push_back({'M','L'});
        } else if (dj > 0) {
            for (int t = 0; t < dj; ++t) out.push_back({'M','R'});
        }

        ci = ti; cj = tj;
    }

    for (auto &p : out) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}