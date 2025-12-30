#include <bits/stdc++.h>
using namespace std;

int get_flat(int x, int y) {
    return x * (x + 1) / 2 + y;
}

vector<pair<int, int>> get_neighbors(int x, int y) {
    vector<pair<int, int>> res;
    // horizontal
    if (y > 0) res.emplace_back(x, y - 1);
    if (y < x) res.emplace_back(x, y + 1);
    // down
    if (x < 29) {
        res.emplace_back(x + 1, y);
        res.emplace_back(x + 1, y + 1);
    }
    // up
    if (x > 0) {
        if (y <= x - 1) res.emplace_back(x - 1, y);
        if (y > 0) res.emplace_back(x - 1, y - 1);
    }
    return res;
}

int main() {
    vector<vector<int>> current(30);
    for (int x = 0; x < 30; ++x) {
        current[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) {
            cin >> current[x][y];
        }
    }
    vector<pair<int, int>> location(465);
    for (int x = 0; x < 30; ++x) {
        for (int y = 0; y <= x; ++y) {
            location[current[x][y]] = {x, y};
        }
    }
    vector<pair<int, int>> order(465);
    int idx = 0;
    for (int x = 0; x < 30; ++x) {
        for (int y = 0; y <= x; ++y) {
            order[idx++] = {x, y};
        }
    }
    vector<array<int, 4>> swaps;
    for (int i = 0; i < 465; ++i) {
        int tx = order[i].first, ty = order[i].second;
        int tnum = i;
        auto [cx, cy] = location[tnum];
        if (cx == tx && cy == ty) continue;
        // BFS
        vector<vector<bool>> vis(30, vector<bool>(30, false));
        vector<vector<pair<int, int>>> par(30, vector<pair<int, int>>(30, {-1, -1}));
        queue<pair<int, int>> q;
        q.emplace(cx, cy);
        vis[cx][cy] = true;
        par[cx][cy] = {-2, -2};
        while (!q.empty()) {
            auto [ux, uy] = q.front();
            q.pop();
            auto neibs = get_neighbors(ux, uy);
            for (auto [nx, ny] : neibs) {
                int f = get_flat(nx, ny);
                if (f >= i && !vis[nx][ny]) {
                    vis[nx][ny] = true;
                    par[nx][ny] = {ux, uy};
                    q.emplace(nx, ny);
                }
            }
        }
        // reconstruct path
        vector<pair<int, int>> path;
        pair<int, int> cur = {tx, ty};
        while (cur != make_pair(cx, cy)) {
            path.push_back(cur);
            cur = par[cur.first][cur.second];
        }
        path.push_back({cx, cy});
        reverse(path.begin(), path.end());
        // perform swaps
        for (size_t j = 0; j + 1 < path.size(); ++j) {
            int x1 = path[j].first, y1 = path[j].second;
            int x2 = path[j + 1].first, y2 = path[j + 1].second;
            int num1 = current[x1][y1], num2 = current[x2][y2];
            current[x1][y1] = num2;
            current[x2][y2] = num1;
            location[num1] = {x2, y2};
            location[num2] = {x1, y1};
            swaps.push_back({x1, y1, x2, y2});
        }
    }
    cout << swaps.size() << endl;
    for (auto& s : swaps) {
        cout << s[0] << " " << s[1] << " " << s[2] << " " << s[3] << endl;
    }
    return 0;
}