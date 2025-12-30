#include <bits/stdc++.h>
using namespace std;

const int N = 10;

int compute_score(const vector<vector<int>>& g) {
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    vector<vector<int>> vis(N, vector<int>(N, 0));
    int total = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (g[r][c] == 0 || vis[r][c]) continue;
            int col = g[r][c];
            int sz = 0;
            queue<pair<int,int>> q;
            q.push({r, c});
            vis[r][c] = 1;
            while (!q.empty()) {
                auto [cr, cc] = q.front(); q.pop();
                ++sz;
                for (int k = 0; k < 4; ++k) {
                    int nr = cr + dr[k];
                    int nc = cc + dc[k];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (vis[nr][nc] || g[nr][nc] != col) continue;
                    vis[nr][nc] = 1;
                    q.push({nr, nc});
                }
            }
            total += sz * sz;
        }
    }
    return total;
}

void tilt(const vector<vector<int>>& src, vector<vector<int>>& dst, char dir) {
    dst.assign(N, vector<int>(N, 0));
    if (dir == 'F') { // up
        for (int c = 0; c < N; ++c) {
            int w = 0;
            for (int r = 0; r < N; ++r) {
                if (src[r][c] != 0) {
                    dst[w][c] = src[r][c];
                    ++w;
                }
            }
        }
    } else if (dir == 'B') { // down
        for (int c = 0; c < N; ++c) {
            int w = N - 1;
            for (int r = N - 1; r >= 0; --r) {
                if (src[r][c] != 0) {
                    dst[w][c] = src[r][c];
                    --w;
                }
            }
        }
    } else if (dir == 'L') { // left
        for (int r = 0; r < N; ++r) {
            int w = 0;
            for (int c = 0; c < N; ++c) {
                if (src[r][c] != 0) {
                    dst[r][w] = src[r][c];
                    ++w;
                }
            }
        }
    } else if (dir == 'R') { // right
        for (int r = 0; r < N; ++r) {
            int w = N - 1;
            for (int c = N - 1; c >= 0; --c) {
                if (src[r][c] != 0) {
                    dst[r][w] = src[r][c];
                    --w;
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; ++i) {
        if (!(cin >> f[i])) return 0;
    }

    vector<vector<int>> board(N, vector<int>(N, 0));
    vector<vector<int>> tmp, bestBoard;

    for (int t = 0; t < 100; ++t) {
        int p;
        if (!(cin >> p)) return 0;

        // place new candy
        int idx = 0;
        bool placed = false;
        for (int r = 0; r < N && !placed; ++r) {
            for (int c = 0; c < N && !placed; ++c) {
                if (board[r][c] == 0) {
                    ++idx;
                    if (idx == p) {
                        board[r][c] = f[t];
                        placed = true;
                    }
                }
            }
        }

        char bestDir = 'F';
        int bestScore = -1;
        const char dirs[4] = {'F', 'B', 'L', 'R'};

        for (int k = 0; k < 4; ++k) {
            char d = dirs[k];
            tilt(board, tmp, d);
            int sc = compute_score(tmp);
            if (sc > bestScore) {
                bestScore = sc;
                bestDir = d;
                bestBoard = tmp;
            }
        }

        board = bestBoard;

        // Output direction (including for t == 99; 100th tilt is harmless on full board)
        cout << bestDir << '\n';
        cout.flush();
    }

    return 0;
}