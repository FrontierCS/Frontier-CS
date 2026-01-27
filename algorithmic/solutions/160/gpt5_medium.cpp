#include <bits/stdc++.h>
using namespace std;

const int N = 10;

using Grid = array<array<int, N>, N>;

Grid tiltGrid(const Grid &g, char dir) {
    Grid res{};
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) res[i][j] = 0;
    if (dir == 'L') {
        for (int r = 0; r < N; r++) {
            int cpos = 0;
            for (int c = 0; c < N; c++) if (g[r][c]) res[r][cpos++] = g[r][c];
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; r++) {
            int cpos = N - 1;
            for (int c = N - 1; c >= 0; c--) if (g[r][c]) res[r][cpos--] = g[r][c];
        }
    } else if (dir == 'F') { // up
        for (int c = 0; c < N; c++) {
            int rpos = 0;
            for (int r = 0; r < N; r++) if (g[r][c]) res[rpos++][c] = g[r][c];
        }
    } else if (dir == 'B') { // down
        for (int c = 0; c < N; c++) {
            int rpos = N - 1;
            for (int r = N - 1; r >= 0; r--) if (g[r][c]) res[rpos--][c] = g[r][c];
        }
    }
    return res;
}

long long heuristic(const Grid &g) {
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    bool vis[N][N] = {};
    long long score = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (g[r][c] == 0 || vis[r][c]) continue;
            int col = g[r][c];
            int sz = 0;
            queue<pair<int,int>> q;
            q.push({r,c});
            vis[r][c] = true;
            while (!q.empty()) {
                auto [rr, cc] = q.front(); q.pop();
                sz++;
                for (int k = 0; k < 4; k++) {
                    int nr = rr + dr[k], nc = cc + dc[k];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (!vis[nr][nc] && g[nr][nc] == col) {
                        vis[nr][nc] = true;
                        q.push({nr,nc});
                    }
                }
            }
            score += 1LL * sz * sz;
        }
    }
    return score;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }
    Grid grid{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) grid[r][c] = 0;

    const vector<char> dirs = {'F','B','L','R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;
        // place candy at p-th empty cell (1-indexed), front-to-back (row-major), left-to-right
        int cnt = 0;
        int pr = -1, pc = -1;
        for (int r = 0; r < N; r++) {
            for (int c = 0; c < N; c++) {
                if (grid[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        pr = r; pc = c;
                        r = N; break;
                    }
                }
            }
        }
        if (pr == -1) { pr = 0; pc = 0; } // fallback (shouldn't happen)
        grid[pr][pc] = f[t];

        // choose best direction by heuristic
        long long bestScore = LLONG_MIN;
        char bestDir = 'F';
        Grid bestGrid = grid;
        for (char d : dirs) {
            Grid ng = tiltGrid(grid, d);
            long long sc = heuristic(ng);
            if (sc > bestScore) {
                bestScore = sc;
                bestDir = d;
                bestGrid = ng;
            }
        }

        // output direction and flush
        cout << bestDir << '\n' << flush;

        // apply move
        grid = bestGrid;
    }

    return 0;
}