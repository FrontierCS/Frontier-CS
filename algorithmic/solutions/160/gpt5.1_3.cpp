#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 10, W = 10;
    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    vector<vector<int>> board(H, vector<int>(W, 0));

    auto tilt = [&](vector<vector<int>> &g, char dir) {
        if (dir == 'F') { // towards row 0
            for (int c = 0; c < W; c++) {
                int ptr = 0;
                for (int r = 0; r < H; r++) {
                    if (g[r][c] != 0) {
                        int v = g[r][c];
                        g[r][c] = 0;
                        g[ptr][c] = v;
                        ptr++;
                    }
                }
            }
        } else if (dir == 'B') { // towards row 9
            for (int c = 0; c < W; c++) {
                int ptr = H - 1;
                for (int r = H - 1; r >= 0; r--) {
                    if (g[r][c] != 0) {
                        int v = g[r][c];
                        g[r][c] = 0;
                        g[ptr][c] = v;
                        ptr--;
                    }
                }
            }
        } else if (dir == 'L') { // towards col 0
            for (int r = 0; r < H; r++) {
                int ptr = 0;
                for (int c = 0; c < W; c++) {
                    if (g[r][c] != 0) {
                        int v = g[r][c];
                        g[r][c] = 0;
                        g[r][ptr] = v;
                        ptr++;
                    }
                }
            }
        } else if (dir == 'R') { // towards col 9
            for (int r = 0; r < H; r++) {
                int ptr = W - 1;
                for (int c = W - 1; c >= 0; c--) {
                    if (g[r][c] != 0) {
                        int v = g[r][c];
                        g[r][c] = 0;
                        g[r][ptr] = v;
                        ptr--;
                    }
                }
            }
        }
    };

    auto evalBoard = [&](const vector<vector<int>> &g) -> long long {
        static int dr[4] = {-1, 1, 0, 0};
        static int dc[4] = {0, 0, -1, 1};
        bool vis[H][W];
        memset(vis, 0, sizeof(vis));
        long long score = 0;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                if (g[r][c] != 0 && !vis[r][c]) {
                    int color = g[r][c];
                    int cnt = 0;
                    queue<pair<int,int>> q;
                    q.push({r, c});
                    vis[r][c] = true;
                    while (!q.empty()) {
                        auto [cr, cc] = q.front();
                        q.pop();
                        cnt++;
                        for (int k = 0; k < 4; k++) {
                            int nr = cr + dr[k];
                            int nc = cc + dc[k];
                            if (nr < 0 || nr >= H || nc < 0 || nc >= W) continue;
                            if (vis[nr][nc]) continue;
                            if (g[nr][nc] == color) {
                                vis[nr][nc] = true;
                                q.push({nr, nc});
                            }
                        }
                    }
                    score += 1LL * cnt * cnt;
                }
            }
        }
        return score;
    };

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        int rNew = -1, cNew = -1, cnt = 0;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                if (board[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        rNew = r;
                        cNew = c;
                        goto foundCell;
                    }
                }
            }
        }
    foundCell:
        if (rNew == -1) {
            rNew = 0;
            cNew = 0;
        }

        char dirs[4] = {'F', 'B', 'L', 'R'};
        long long bestScore = -1;
        char bestDir = 'F';

        for (char d : dirs) {
            vector<vector<int>> tmp = board;
            tmp[rNew][cNew] = f[t];
            tilt(tmp, d);
            long long sc = evalBoard(tmp);
            if (sc > bestScore) {
                bestScore = sc;
                bestDir = d;
            }
        }

        board[rNew][cNew] = f[t];
        tilt(board, bestDir);

        cout << bestDir << '\n' << flush;
    }

    return 0;
}