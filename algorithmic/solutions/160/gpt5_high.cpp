#include <bits/stdc++.h>
using namespace std;

using Board = array<array<int,10>,10>;

static inline Board tiltBoard(const Board &b, char dir) {
    Board nb{};
    for (int i = 0; i < 10; i++) for (int j = 0; j < 10; j++) nb[i][j] = 0;
    if (dir == 'F') {
        for (int c = 0; c < 10; c++) {
            int pos = 0;
            for (int r = 0; r < 10; r++) if (b[r][c] != 0) nb[pos++][c] = b[r][c];
        }
    } else if (dir == 'B') {
        for (int c = 0; c < 10; c++) {
            int pos = 9;
            for (int r = 9; r >= 0; r--) if (b[r][c] != 0) nb[pos--][c] = b[r][c];
        }
    } else if (dir == 'L') {
        for (int r = 0; r < 10; r++) {
            int pos = 0;
            for (int c = 0; c < 10; c++) if (b[r][c] != 0) nb[r][pos++] = b[r][c];
        }
    } else if (dir == 'R') {
        for (int r = 0; r < 10; r++) {
            int pos = 9;
            for (int c = 9; c >= 0; c--) if (b[r][c] != 0) nb[r][pos--] = b[r][c];
        }
    }
    return nb;
}

static inline long long compScore(const Board &b) {
    bool vis[10][10] = {};
    long long sum = 0;
    int dr[4] = {1,-1,0,0};
    int dc[4] = {0,0,1,-1};
    for (int r = 0; r < 10; r++) {
        for (int c = 0; c < 10; c++) {
            if (b[r][c] == 0 || vis[r][c]) continue;
            int color = b[r][c];
            int sz = 0;
            queue<pair<int,int>> q;
            q.emplace(r,c);
            vis[r][c] = true;
            while (!q.empty()) {
                auto [rr, cc] = q.front(); q.pop();
                sz++;
                for (int k = 0; k < 4; k++) {
                    int nr = rr + dr[k], nc = cc + dc[k];
                    if (nr < 0 || nr >= 10 || nc < 0 || nc >= 10) continue;
                    if (!vis[nr][nc] && b[nr][nc] == color) {
                        vis[nr][nc] = true;
                        q.emplace(nr, nc);
                    }
                }
            }
            sum += 1LL * sz * sz;
        }
    }
    return sum;
}

static inline long long adjScore(const Board &b) {
    long long adj = 0;
    for (int r = 0; r < 10; r++) {
        for (int c = 0; c+1 < 10; c++) {
            if (b[r][c] != 0 && b[r][c] == b[r][c+1]) adj++;
        }
    }
    for (int r = 0; r+1 < 10; r++) {
        for (int c = 0; c < 10; c++) {
            if (b[r][c] != 0 && b[r][c] == b[r+1][c]) adj++;
        }
    }
    return adj;
}

static inline long long distPenalty(const Board &b) {
    // Assign targets: flavor 1 -> top (F), flavor 2 -> bottom (B), flavor 3 -> left (L)
    long long s = 0;
    for (int r = 0; r < 10; r++) {
        for (int c = 0; c < 10; c++) {
            int v = b[r][c];
            if (v == 0) continue;
            if (v == 1) s += r;
            else if (v == 2) s += (9 - r);
            else s += c; // v == 3
        }
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    Board grid{};
    for (int i = 0; i < 10; i++) for (int j = 0; j < 10; j++) grid[i][j] = 0;

    char prev = 'F';
    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        int rr = -1, cc = -1, cnt = 0;
        for (int r = 0; r < 10 && rr == -1; r++) {
            for (int c = 0; c < 10; c++) {
                if (grid[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        rr = r; cc = c;
                        break;
                    }
                }
            }
        }
        if (rr != -1) grid[rr][cc] = f[t];

        vector<char> dirs = {'F','B','L','R'};
        long long bestScore = LLONG_MIN;
        char bestDir = 'F';
        Board bestBoard = grid;

        for (char d : dirs) {
            Board nb = tiltBoard(grid, d);
            long long sComp = compScore(nb);
            long long sAdj = adjScore(nb);
            long long sDist = distPenalty(nb);
            // Weighted objective: prioritize component score, then adjacency, then distance penalty
            long long s = sComp * 1000000LL + sAdj * 1000LL - sDist;
            if (s > bestScore) {
                bestScore = s;
                bestDir = d;
                bestBoard = nb;
            }
        }

        cout << bestDir << '\n' << flush;
        grid = bestBoard;
        prev = bestDir;
    }
    return 0;
}