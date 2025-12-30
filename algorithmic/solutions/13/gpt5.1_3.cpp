#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    const int T = 3000;
    vector<pair<int,int>> moves;
    moves.reserve(T);
    set<pair<int,int>> used;

    auto add_cell = [&](int x, int y) {
        if (x < 1 || x > T || y < 1 || y > T) return;
        pair<int,int> p = {x, y};
        if (used.insert(p).second) {
            moves.push_back(p);
        }
    };

    // Build traps along bottom row y = 1 for x = 2..251 (250 traps)
    for (int x = 2; x <= 251 && (int)moves.size() < T; ++x) {
        add_cell(x - 1, 1);
        if ((int)moves.size() >= T) break;
        add_cell(x + 1, 1);
        if ((int)moves.size() >= T) break;
        add_cell(x - 1, 2);
        if ((int)moves.size() >= T) break;
        add_cell(x, 2);
        if ((int)moves.size() >= T) break;
        add_cell(x + 1, 2);
        if ((int)moves.size() >= T) break;
    }

    // Build traps along left column x = 1 for y = 2..251 (250 traps)
    for (int y = 2; y <= 251 && (int)moves.size() < T; ++y) {
        add_cell(1, y - 1);
        if ((int)moves.size() >= T) break;
        add_cell(1, y + 1);
        if ((int)moves.size() >= T) break;
        add_cell(2, y - 1);
        if ((int)moves.size() >= T) break;
        add_cell(2, y);
        if ((int)moves.size() >= T) break;
        add_cell(2, y + 1);
        if ((int)moves.size() >= T) break;
    }

    // If we still have room, just fill with (1,1)
    while ((int)moves.size() < T) {
        moves.push_back({1, 1});
    }

    int rx = sx, ry = sy;
    for (int i = 0; i < T; ++i) {
        cout << moves[i].first << ' ' << moves[i].second << '\n';
        cout.flush();
        if (!(cin >> rx >> ry)) break;
        if (rx == 0 && ry == 0) break;
    }

    return 0;
}