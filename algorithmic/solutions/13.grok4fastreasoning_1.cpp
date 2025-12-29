#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T = 3000;
    vector<vector<char>> is_black(T + 1, vector<char>(T + 1, 0));
    int rx, ry;
    cin >> rx >> ry;
    int curr_k = rx + ry + 1;
    set<pair<int, int>> remaining;
    auto generate_wall = [&](int kk) {
        for (int x = 1; x < kk; ++x) {
            int y = kk - x;
            if (y >= 1 && y <= T) {
                remaining.insert({x, y});
            }
        }
    };
    generate_wall(curr_k);
    generate_wall(curr_k + 1);
    while (true) {
        pair<int, int> to_paint = {-1, -1};
        int min_d = INT_MAX / 2;
        if (!remaining.empty()) {
            for (auto p : remaining) {
                int d = max(abs(p.first - rx), abs(p.second - ry));
                if (d < min_d || (d == min_d && (p.first < to_paint.first || (p.first == to_paint.first && p.second < to_paint.second)))) {
                    min_d = d;
                    to_paint = p;
                }
            }
            if (to_paint.first != -1) {
                cout << to_paint.first << " " << to_paint.second << '\n';
                cout.flush();
                is_black[to_paint.first][to_paint.second] = 1;
                remaining.erase(to_paint);
            }
        } else {
            bool found_adj = false;
            for (int dx = -1; dx <= 1; ++dx) {
                for (int dy = -1; dy <= 1; ++dy) {
                    if (dx == 0 && dy == 0) continue;
                    int nx = rx + dx, ny = ry + dy;
                    if (nx < 1 || ny < 1 || nx > T || ny > T) continue;
                    if (is_black[nx][ny] == 0) {
                        to_paint = {nx, ny};
                        found_adj = true;
                        goto print_adj;
                    }
                }
            }
        print_adj:
            if (!found_adj) {
                to_paint = {rx, ry};
            }
            cout << to_paint.first << " " << to_paint.second << '\n';
            cout.flush();
            is_black[to_paint.first][to_paint.second] = 1;
        }
        int nx, ny;
        cin >> nx >> ny;
        if (nx == 0 && ny == 0) return 0;
        rx = nx;
        ry = ny;
        if (rx + ry > curr_k + 1) {
            curr_k = rx + ry + 1;
            remaining.clear();
            generate_wall(curr_k);
            generate_wall(curr_k + 1);
        }
    }
    return 0;
}