#include <bits/stdc++.h>
using namespace std;

// tilt the grid in direction dir
vector<vector<int>> tilt(const vector<vector<int>>& g, char dir) {
    vector<vector<int>> ng(10, vector<int>(10, 0));
    if (dir == 'L') {
        for (int r = 0; r < 10; ++r) {
            vector<int> flavors;
            for (int c = 0; c < 10; ++c)
                if (g[r][c]) flavors.push_back(g[r][c]);
            int idx = 0;
            for (int f : flavors) ng[r][idx++] = f;
        }
    } else if (dir == 'R') {
        for (int r = 0; r < 10; ++r) {
            vector<int> flavors;
            for (int c = 9; c >= 0; --c)
                if (g[r][c]) flavors.push_back(g[r][c]);
            int idx = 9;
            for (int f : flavors) ng[r][idx--] = f;
        }
    } else if (dir == 'F') {
        for (int c = 0; c < 10; ++c) {
            vector<int> flavors;
            for (int r = 0; r < 10; ++r)
                if (g[r][c]) flavors.push_back(g[r][c]);
            int idx = 0;
            for (int f : flavors) ng[idx++][c] = f;
        }
    } else if (dir == 'B') {
        for (int c = 0; c < 10; ++c) {
            vector<int> flavors;
            for (int r = 9; r >= 0; --r)
                if (g[r][c]) flavors.push_back(g[r][c]);
            int idx = 9;
            for (int f : flavors) ng[idx--][c] = f;
        }
    }
    return ng;
}

// compute sum of squares of connected component sizes
int sum_squares(const vector<vector<int>>& g) {
    bool vis[10][10] = {};
    const int dr[4] = {1, -1, 0, 0};
    const int dc[4] = {0, 0, 1, -1};
    int total = 0;
    for (int r = 0; r < 10; ++r) {
        for (int c = 0; c < 10; ++c) {
            if (g[r][c] && !vis[r][c]) {
                int flavor = g[r][c];
                queue<pair<int,int>> q;
                q.push({r, c});
                vis[r][c] = true;
                int sz = 0;
                while (!q.empty()) {
                    auto [cr, cc] = q.front(); q.pop();
                    ++sz;
                    for (int d = 0; d < 4; ++d) {
                        int nr = cr + dr[d];
                        int nc = cc + dc[d];
                        if (nr >= 0 && nr < 10 && nc >= 0 && nc < 10 &&
                            !vis[nr][nc] && g[nr][nc] == flavor) {
                            vis[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }
                total += sz * sz;
            }
        }
    }
    return total;
}

// compute total Manhattan distance to assigned corners
int total_distance(const vector<vector<int>>& g, const pair<int,int> target[]) {
    int dist = 0;
    for (int r = 0; r < 10; ++r)
        for (int c = 0; c < 10; ++c)
            if (g[r][c]) {
                int fl = g[r][c];
                auto [tr, tc] = target[fl];
                dist += abs(r - tr) + abs(c - tc);
            }
    return dist;
}

int main() {
    // read the 100 flavors
    int f[100];
    for (int i = 0; i < 100; ++i) cin >> f[i];

    // assign target corners for each flavor
    pair<int,int> target[4];   // indices 1..3
    target[1] = {0, 0}; // front-left
    target[2] = {0, 9}; // front-right
    target[3] = {9, 0}; // back-left

    // current grid, initially empty
    vector<vector<int>> grid(10, vector<int>(10, 0));

    // process 100 candies
    for (int t = 0; t < 100; ++t) {
        int p;
        cin >> p;

        // find the p-th empty cell (row-major order)
        int cnt = 0, rr = -1, cc = -1;
        for (int r = 0; r < 10 && rr == -1; ++r) {
            for (int c = 0; c < 10; ++c) {
                if (grid[r][c] == 0) {
                    ++cnt;
                    if (cnt == p) {
                        rr = r; cc = c;
                        break;
                    }
                }
            }
        }
        // place the candy
        grid[rr][cc] = f[t];

        // evaluate the four possible tilt directions
        char dirs[4] = {'F', 'B', 'L', 'R'};
        char best_dir = 'F';
        int best_sum_sq = -1, best_dist = 1e9;
        for (char dir : dirs) {
            auto ng = tilt(grid, dir);
            int sum_sq = sum_squares(ng);
            int dist = total_distance(ng, target);
            if (sum_sq > best_sum_sq || (sum_sq == best_sum_sq && dist < best_dist)) {
                best_sum_sq = sum_sq;
                best_dist = dist;
                best_dir = dir;
            }
        }

        // output the chosen direction
        cout << best_dir << endl;

        // apply the tilt to the real box
        grid = tilt(grid, best_dir);
    }

    return 0;
}