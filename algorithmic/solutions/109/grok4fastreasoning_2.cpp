#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    int sr, sc;
    cin >> sr >> sc;
    vector<pair<int, int>> path;
    bool vis[667][667] = {};
    path.push_back({sr, sc});
    vis[sr][sc] = true;
    pair<int, int> cur = {sr, sc};
    int dx[8] = {1, 1, -1, -1, 2, 2, -2, -2};
    int dy[8] = {2, -2, 2, -2, 1, -1, 1, -1};
    while (true) {
        vector<pair<int, int>> candidates;
        for (int d = 0; d < 8; d++) {
            int nr = cur.first + dx[d];
            int nc = cur.second + dy[d];
            if (nr >= 1 && nr <= N && nc >= 1 && nc <= N && !vis[nr][nc]) {
                candidates.push_back({nr, nc});
            }
        }
        if (candidates.empty()) break;
        vector<tuple<int, int, int>> options;
        for (auto [x, y] : candidates) {
            int deg = 0;
            for (int d = 0; d < 8; d++) {
                int nnr = x + dx[d];
                int nnc = y + dy[d];
                if (nnr >= 1 && nnr <= N && nnc >= 1 && nnc <= N && !vis[nnr][nnc]) deg++;
            }
            options.push_back({deg, x, y});
        }
        sort(options.begin(), options.end());
        auto [_, nx, ny] = options[0];
        path.push_back({nx, ny});
        vis[nx][ny] = true;
        cur = {nx, ny};
    }
    int len = path.size();
    cout << len << "\n";
    for (auto [x, y] : path) {
        cout << x << " " << y << "\n";
    }
    return 0;
}