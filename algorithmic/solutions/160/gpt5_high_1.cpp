#include <bits/stdc++.h>
using namespace std;

static const int N = 10;

using Grid = array<array<int, N>, N>;

Grid tilt(const Grid& g, char dir) {
    Grid ng{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) ng[r][c] = 0;
    if (dir == 'F') {
        for (int c = 0; c < N; c++) {
            int idx = 0;
            for (int r = 0; r < N; r++) if (g[r][c] != 0) ng[idx++][c] = g[r][c];
        }
    } else if (dir == 'B') {
        for (int c = 0; c < N; c++) {
            int idx = N - 1;
            for (int r = N - 1; r >= 0; r--) if (g[r][c] != 0) ng[idx--][c] = g[r][c];
        }
    } else if (dir == 'L') {
        for (int r = 0; r < N; r++) {
            int idx = 0;
            for (int c = 0; c < N; c++) if (g[r][c] != 0) ng[r][idx++] = g[r][c];
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; r++) {
            int idx = N - 1;
            for (int c = N - 1; c >= 0; c--) if (g[r][c] != 0) ng[r][idx--] = g[r][c];
        }
    }
    return ng;
}

long long componentScore(const Grid& g) {
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    bool vis[N][N] = {};
    long long score = 0;
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) {
        if (g[r][c] == 0 || vis[r][c]) continue;
        int color = g[r][c];
        int cnt = 0;
        queue<pair<int,int>> q;
        q.push({r,c});
        vis[r][c] = true;
        while (!q.empty()) {
            auto [rr, cc] = q.front(); q.pop();
            cnt++;
            for (int k = 0; k < 4; k++) {
                int nr = rr + dr[k], nc = cc + dc[k];
                if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                if (!vis[nr][nc] && g[nr][nc] == color) {
                    vis[nr][nc] = true;
                    q.push({nr, nc});
                }
            }
        }
        score += 1LL * cnt * cnt;
    }
    return score;
}

long long distanceScore(const Grid& g, const array<int, 4>& tr, const array<int, 4>& tc) {
    long long sum = 0;
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) {
        int v = g[r][c];
        if (v == 0) continue;
        sum += abs(r - tr[v]) + abs(c - tc[v]);
    }
    return sum;
}

pair<int,int> findEmptyByIndex(const Grid& g, int p) {
    int cnt = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (g[r][c] == 0) {
                cnt++;
                if (cnt == p) return {r, c};
            }
        }
    }
    return {-1, -1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    // Assign targets: flavor 1 -> (0,0), flavor 2 -> (0,9), flavor 3 -> (9,0)
    array<int, 4> tr = {0, 0, 0, 9};
    array<int, 4> tc = {0, 0, 9, 0};

    Grid grid{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) grid[r][c] = 0;

    for (int t = 0; t < 100; t++) {
        int p; 
        if (!(cin >> p)) return 0;

        auto [r, c] = findEmptyByIndex(grid, p);
        if (r == -1) r = 0, c = 0;
        grid[r][c] = f[t];

        char bestDir = 'F';
        long long bestComp = -1;
        long long bestDist = (1LL<<60);

        const char dirs[4] = {'F','B','L','R'};
        for (char d : dirs) {
            Grid g2 = tilt(grid, d);
            long long comp = componentScore(g2);
            long long dist = distanceScore(g2, tr, tc);
            if (comp > bestComp || (comp == bestComp && dist < bestDist)) {
                bestComp = comp;
                bestDist = dist;
                bestDir = d;
            }
        }

        cout << bestDir << '\n' << flush;

        grid = tilt(grid, bestDir);
    }

    return 0;
}