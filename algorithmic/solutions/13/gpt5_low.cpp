#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int T = 3000;
    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    // Generate a sequence of up to T moves within [1..T]x[1..T], row-major zigzag to stay local
    vector<pair<int,int>> moves;
    moves.reserve(T);
    int cnt = 0;
    for (int y = 1; y <= T && cnt < T; ++y) {
        if (y % 2 == 1) {
            for (int x = 1; x <= T && cnt < T; ++x) {
                moves.emplace_back(x, y);
                ++cnt;
            }
        } else {
            for (int x = T; x >= 1 && cnt < T; --x) {
                moves.emplace_back(x, y);
                ++cnt;
            }
        }
    }

    int rx = sx, ry = sy;
    for (int i = 0; i < (int)moves.size(); ++i) {
        cout << moves[i].first << " " << moves[i].second << "\n";
        cout.flush();
        if (!(cin >> rx >> ry)) break;
        if (rx == 0 && ry == 0) break;
    }
    return 0;
}