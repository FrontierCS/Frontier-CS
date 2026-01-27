#include <bits/stdc++.h>
using namespace std;

static const int H = 10;
static const int W = 10;

using Grid = array<array<int, W>, H>;

Grid tilt(const Grid& g, char dir) {
    Grid res{};
    for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) res[y][x] = 0;
    if (dir == 'L') {
        for (int y = 0; y < H; y++) {
            int w = 0;
            for (int x = 0; x < W; x++) {
                if (g[y][x] != 0) res[y][w++] = g[y][x];
            }
        }
    } else if (dir == 'R') {
        for (int y = 0; y < H; y++) {
            int w = W - 1;
            for (int x = W - 1; x >= 0; x--) {
                if (g[y][x] != 0) res[y][w--] = g[y][x];
            }
        }
    } else if (dir == 'F') { // up
        for (int x = 0; x < W; x++) {
            int h = 0;
            for (int y = 0; y < H; y++) {
                if (g[y][x] != 0) res[h++][x] = g[y][x];
            }
        }
    } else if (dir == 'B') { // down
        for (int x = 0; x < W; x++) {
            int h = H - 1;
            for (int y = H - 1; y >= 0; y--) {
                if (g[y][x] != 0) res[h--][x] = g[y][x];
            }
        }
    }
    return res;
}

long long evalScore(const Grid& g) {
    bool vis[H][W];
    memset(vis, 0, sizeof(vis));
    long long score = 0;
    int dy[4] = {-1, 1, 0, 0};
    int dx[4] = {0, 0, -1, 1};
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            if (g[y][x] == 0 || vis[y][x]) continue;
            int col = g[y][x];
            int cnt = 0;
            queue<pair<int,int>> q;
            q.push({y,x});
            vis[y][x] = true;
            while (!q.empty()) {
                auto [cy, cx] = q.front(); q.pop();
                cnt++;
                for (int d = 0; d < 4; d++) {
                    int ny = cy + dy[d], nx = cx + dx[d];
                    if (ny < 0 || ny >= H || nx < 0 || nx >= W) continue;
                    if (vis[ny][nx]) continue;
                    if (g[ny][nx] != col) continue;
                    vis[ny][nx] = true;
                    q.push({ny,nx});
                }
            }
            score += 1LL * cnt * cnt;
        }
    }
    return score;
}

// Compute final position of the newly placed candy after a tilt, using counts on the current grid (with the candy placed)
pair<int,int> finalPosAfterTilt(const Grid& g, int ry, int rx, char dir) {
    if (dir == 'L') {
        int cnt = 0;
        for (int x = 0; x <= rx; x++) if (g[ry][x] != 0) cnt++;
        return {ry, cnt - 1};
    } else if (dir == 'R') {
        int cnt = 0;
        for (int x = rx; x < W; x++) if (g[ry][x] != 0) cnt++;
        return {ry, W - cnt};
    } else if (dir == 'F') {
        int cnt = 0;
        for (int y = 0; y <= ry; y++) if (g[y][rx] != 0) cnt++;
        return {cnt - 1, rx};
    } else { // 'B'
        int cnt = 0;
        for (int y = ry; y < H; y++) if (g[y][rx] != 0) cnt++;
        return {H - cnt, rx};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    Grid board{};
    for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) board[y][x] = 0;

    const vector<char> dirs = {'F','B','L','R'};
    // target corners for tie-break based on flavor: 1->(0,0), 2->(9,0), 3->(9,9)
    auto targetCorner = [&](int flavor) -> pair<int,int> {
        if (flavor == 1) return {0, 0};
        if (flavor == 2) return {9, 0};
        return {9, 9};
    };

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        // place candy at p-th empty cell in row-major order
        int placed_y = -1, placed_x = -1;
        int cntEmpty = 0;
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                if (board[y][x] == 0) {
                    cntEmpty++;
                    if (cntEmpty == p) {
                        board[y][x] = f[t];
                        placed_y = y; placed_x = x;
                        y = H; break;
                    }
                }
            }
        }

        // If this is the last move and board becomes full, still select a direction (optional)
        long long bestScore = LLONG_MIN;
        char bestDir = 'F';
        Grid bestBoard = board;

        for (char dir : dirs) {
            Grid after = tilt(board, dir);
            long long S = evalScore(after);

            // tie-break: prefer moving the newly placed candy closer to its target corner
            // compute position of newly placed candy after this tilt (using board with the candy placed)
            auto [ny, nx] = finalPosAfterTilt(board, placed_y, placed_x, dir);
            auto [ty, tx] = targetCorner(f[t]);
            int manhattan = abs(ny - ty) + abs(nx - tx);

            long long composite = S * 1000LL - manhattan; // small tie-breaker
            if (composite > bestScore) {
                bestScore = composite;
                bestDir = dir;
                bestBoard = after;
            }
        }

        // Output chosen direction (including at t==99 as allowed)
        cout << bestDir << '\n' << flush;

        // Update board to the chosen state
        board = bestBoard;
    }

    return 0;
}