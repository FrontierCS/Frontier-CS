#include <bits/stdc++.h>
using namespace std;

const int H = 10;
const int W = 10;

void tiltF(int b[H][W]) { // forward: to smaller row index
    for (int c = 0; c < W; c++) {
        int line[H];
        int k = 0;
        for (int r = 0; r < H; r++) {
            if (b[r][c] != 0) line[k++] = b[r][c];
        }
        int r = 0;
        for (int i = 0; i < k; i++, r++) b[r][c] = line[i];
        for (; r < H; r++) b[r][c] = 0;
    }
}

void tiltB(int b[H][W]) { // backward: to larger row index
    for (int c = 0; c < W; c++) {
        int line[H];
        int k = 0;
        for (int r = 0; r < H; r++) {
            if (b[r][c] != 0) line[k++] = b[r][c];
        }
        int r = H - 1;
        for (int i = k - 1; i >= 0; i--, r--) b[r][c] = line[i];
        for (; r >= 0; r--) b[r][c] = 0;
    }
}

void tiltL(int b[H][W]) { // left: to smaller col index
    for (int r = 0; r < H; r++) {
        int line[W];
        int k = 0;
        for (int c = 0; c < W; c++) {
            if (b[r][c] != 0) line[k++] = b[r][c];
        }
        int c = 0;
        for (int i = 0; i < k; i++, c++) b[r][c] = line[i];
        for (; c < W; c++) b[r][c] = 0;
    }
}

void tiltR(int b[H][W]) { // right: to larger col index
    for (int r = 0; r < H; r++) {
        int line[W];
        int k = 0;
        for (int c = 0; c < W; c++) {
            if (b[r][c] != 0) line[k++] = b[r][c];
        }
        int c = W - 1;
        for (int i = k - 1; i >= 0; i--, c--) b[r][c] = line[i];
        for (; c >= 0; c--) b[r][c] = 0;
    }
}

long long connectivityScore(int b[H][W]) {
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    bool vis[H][W] = {};
    long long sumSq = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            if (b[r][c] != 0 && !vis[r][c]) {
                int color = b[r][c];
                int sz = 0;
                queue<pair<int,int>> q;
                vis[r][c] = true;
                q.emplace(r, c);
                while (!q.empty()) {
                    auto [cr, cc] = q.front();
                    q.pop();
                    sz++;
                    for (int k = 0; k < 4; k++) {
                        int nr = cr + dr[k];
                        int nc = cc + dc[k];
                        if (nr < 0 || nr >= H || nc < 0 || nc >= W) continue;
                        if (!vis[nr][nc] && b[nr][nc] == color) {
                            vis[nr][nc] = true;
                            q.emplace(nr, nc);
                        }
                    }
                }
                sumSq += 1LL * sz * sz;
            }
        }
    }
    return sumSq;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavor(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> flavor[i])) return 0;
    }

    int board[H][W];
    for (int r = 0; r < H; r++)
        for (int c = 0; c < W; c++)
            board[r][c] = 0;

    const char dirChar[4] = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        // Find placement cell (p-th empty in row-major order)
        int cnt = 0;
        int pr = -1, pc = -1;
        for (int r = 0; r < H && pr == -1; r++) {
            for (int c = 0; c < W; c++) {
                if (board[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        pr = r;
                        pc = c;
                        break;
                    }
                }
            }
        }
        if (pr == -1) return 0; // should not happen

        board[pr][pc] = flavor[t];

        // Choose best tilt direction greedily
        char bestDir = 'F';
        long long bestNum = -1;

        for (int d = 0; d < 4; d++) {
            int tmp[H][W];
            for (int r = 0; r < H; r++)
                for (int c = 0; c < W; c++)
                    tmp[r][c] = board[r][c];

            if (d == 0) tiltF(tmp);
            else if (d == 1) tiltB(tmp);
            else if (d == 2) tiltL(tmp);
            else tiltR(tmp);

            long long num = connectivityScore(tmp);
            if (num > bestNum) {
                bestNum = num;
                bestDir = dirChar[d];
            }
        }

        cout << bestDir << endl;

        // Apply chosen tilt to actual board
        if (bestDir == 'F') tiltF(board);
        else if (bestDir == 'B') tiltB(board);
        else if (bestDir == 'L') tiltL(board);
        else tiltR(board);
    }

    return 0;
}