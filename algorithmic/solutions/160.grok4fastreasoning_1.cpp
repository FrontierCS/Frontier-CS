#include <bits/stdc++.h>
using namespace std;

int flood(const vector<vector<int>>& g, vector<vector<bool>>& vis, int sr, int sc, int flav) {
    int dr[] = {-1, 0, 1, 0};
    int dc[] = {0, 1, 0, -1};
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    int sz = 1;
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr >= 0 && nr < 10 && nc >= 0 && nc < 10 && !vis[nr][nc] && g[nr][nc] == flav) {
                vis[nr][nc] = true;
                q.push({nr, nc});
                sz++;
            }
        }
    }
    return sz;
}

long long compute(const vector<vector<int>>& g) {
    vector<vector<bool>> vis(10, vector<bool>(10, false));
    long long sum = 0;
    for (int r = 0; r < 10; r++) {
        for (int c = 0; c < 10; c++) {
            if (g[r][c] != 0 && !vis[r][c]) {
                int sz = flood(g, vis, r, c, g[r][c]);
                sum += 1LL * sz * sz;
            }
        }
    }
    return sum;
}

void apply_tilt(vector<vector<int>>& g, char dir) {
    if (dir == 'F') { // up
        for (int c = 0; c < 10; c++) {
            vector<int> candies;
            for (int r = 0; r < 10; r++) if (g[r][c] != 0) candies.push_back(g[r][c]);
            for (int r = 0; r < 10; r++) g[r][c] = (r < (int)candies.size() ? candies[r] : 0);
        }
    } else if (dir == 'B') { // down
        for (int c = 0; c < 10; c++) {
            vector<int> candies;
            for (int r = 0; r < 10; r++) if (g[r][c] != 0) candies.push_back(g[r][c]);
            int k = candies.size();
            for (int r = 0; r < 10; r++) g[r][c] = (r >= 10 - k ? candies[r - (10 - k)] : 0);
        }
    } else if (dir == 'L') { // left
        for (int r = 0; r < 10; r++) {
            vector<int> candies;
            for (int c = 0; c < 10; c++) if (g[r][c] != 0) candies.push_back(g[r][c]);
            for (int c = 0; c < 10; c++) g[r][c] = (c < (int)candies.size() ? candies[c] : 0);
        }
    } else if (dir == 'R') { // right
        for (int r = 0; r < 10; r++) {
            vector<int> candies;
            for (int c = 0; c < 10; c++) if (g[r][c] != 0) candies.push_back(g[r][c]);
            int k = candies.size();
            for (int c = 0; c < 10; c++) g[r][c] = (c >= 10 - k ? candies[c - (10 - k)] : 0);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    vector<int> f(100);
    for (auto& x : f) cin >> x;
    vector<vector<int>> grid(10, vector<int>(10, 0));
    string dirs = "FBLR";
    for (int t = 0; t < 100; t++) {
        int p;
        cin >> p;
        p--;
        int er = -1, ec = -1;
        int cnt = 0;
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 10; c++) {
                if (grid[r][c] == 0) {
                    if (cnt == p) {
                        er = r;
                        ec = c;
                        goto placed;
                    }
                    cnt++;
                }
            }
        }
    placed:
        grid[er][ec] = f[t];
        long long best = -1;
        char bdir;
        for (char d : dirs) {
            auto temp = grid;
            apply_tilt(temp, d);
            long long sc = compute(temp);
            if (sc > best) {
                best = sc;
                bdir = d;
            }
        }
        cout << bdir << '\n' << flush;
        apply_tilt(grid, bdir);
    }
    return 0;
}