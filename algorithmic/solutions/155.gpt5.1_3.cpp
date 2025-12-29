#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    const int H = 20, W = 20;
    vector<string> h(H), v(H - 1);
    for (int i = 0; i < H; ++i) cin >> h[i];
    for (int i = 0; i < H - 1; ++i) cin >> v[i];

    vector<vector<bool>> visited(H, vector<bool>(W, false));
    vector<vector<pair<int,int>>> prev(H, vector<pair<int,int>>(W, {-1, -1}));
    vector<vector<char>> prevDir(H, vector<char>(W, '?'));

    queue<pair<int,int>> q;
    q.push({si, sj});
    visited[si][sj] = true;

    auto in_bounds = [&](int x, int y) {
        return 0 <= x && x < H && 0 <= y && y < W;
    };

    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        if (i == ti && j == tj) break;

        // Up
        if (i > 0 && !visited[i-1][j] && v[i-1][j] == '0') {
            visited[i-1][j] = true;
            prev[i-1][j] = {i, j};
            prevDir[i-1][j] = 'U';
            q.push({i-1, j});
        }
        // Down
        if (i < H-1 && !visited[i+1][j] && v[i][j] == '0') {
            visited[i+1][j] = true;
            prev[i+1][j] = {i, j};
            prevDir[i+1][j] = 'D';
            q.push({i+1, j});
        }
        // Left
        if (j > 0 && !visited[i][j-1] && h[i][j-1] == '0') {
            visited[i][j-1] = true;
            prev[i][j-1] = {i, j};
            prevDir[i][j-1] = 'L';
            q.push({i, j-1});
        }
        // Right
        if (j < W-1 && !visited[i][j+1] && h[i][j] == '0') {
            visited[i][j+1] = true;
            prev[i][j+1] = {i, j};
            prevDir[i][j+1] = 'R';
            q.push({i, j+1});
        }
    }

    string path;
    if (visited[ti][tj]) {
        int ci = ti, cj = tj;
        while (!(ci == si && cj == sj)) {
            char d = prevDir[ci][cj];
            path.push_back(d);
            auto [pi, pj] = prev[ci][cj];
            ci = pi; cj = pj;
        }
        reverse(path.begin(), path.end());
    }

    if (path.size() > 200 || !visited[ti][tj]) {
        // Fallback: simple dummy path of length 200
        string fallback(200, 'D');
        cout << fallback << '\n';
    } else {
        cout << path << '\n';
    }

    return 0;
}