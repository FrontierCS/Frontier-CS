#include <bits/stdc++.h>
using namespace std;

using Grid = array<array<int, 10>, 10>;

Grid slide(const Grid& g, int dir) {
    Grid ng{};
    for (int y = 0; y < 10; ++y) for (int x = 0; x < 10; ++x) ng[y][x] = 0;
    if (dir == 2) { // L
        for (int y = 0; y < 10; ++y) {
            int k = 0;
            for (int x = 0; x < 10; ++x) if (g[y][x]) ng[y][k++] = g[y][x];
        }
    } else if (dir == 3) { // R
        for (int y = 0; y < 10; ++y) {
            int k = 9;
            for (int x = 9; x >= 0; --x) if (g[y][x]) ng[y][k--] = g[y][x];
        }
    } else if (dir == 0) { // F (up)
        for (int x = 0; x < 10; ++x) {
            int k = 0;
            for (int y = 0; y < 10; ++y) if (g[y][x]) ng[k++][x] = g[y][x];
        }
    } else { // B (down)
        for (int x = 0; x < 10; ++x) {
            int k = 9;
            for (int y = 9; y >= 0; --y) if (g[y][x]) ng[k--][x] = g[y][x];
        }
    }
    return ng;
}

long long score_grid(const Grid& g) {
    static const int dy[4] = {-1, 1, 0, 0};
    static const int dx[4] = {0, 0, -1, 1};
    bool vis[10][10] = {};
    long long s = 0;
    for (int y = 0; y < 10; ++y) {
        for (int x = 0; x < 10; ++x) {
            if (g[y][x] == 0 || vis[y][x]) continue;
            int col = g[y][x];
            int cnt = 0;
            queue<pair<int,int>> q;
            q.push({y,x});
            vis[y][x] = true;
            while (!q.empty()) {
                auto [cy, cx] = q.front(); q.pop();
                cnt++;
                for (int d = 0; d < 4; ++d) {
                    int ny = cy + dy[d], nx = cx + dx[d];
                    if (ny < 0 || ny >= 10 || nx < 0 || nx >= 10) continue;
                    if (!vis[ny][nx] && g[ny][nx] == col) {
                        vis[ny][nx] = true;
                        q.push({ny, nx});
                    }
                }
            }
            s += 1LL * cnt * cnt;
        }
    }
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<int> f(100);
    for (int i = 0; i < 100; ++i) {
        if (!(cin >> f[i])) return 0;
    }
    Grid grid{};
    for (int y = 0; y < 10; ++y) for (int x = 0; x < 10; ++x) grid[y][x] = 0;

    const char dirc[4] = {'F','B','L','R'};
    auto preferred_dir = [&](int flavor)->int{
        if (flavor == 1) return 0; // F
        if (flavor == 2) return 1; // B
        return 3; // flavor 3 -> R
    };

    for (int t = 0; t < 100; ++t) {
        int p;
        if (!(cin >> p)) p = 1;
        // Place candy at p-th empty cell (front-to-back y=0..9, left-to-right x=0..9)
        int cnt = 0;
        int py = -1, px = -1;
        for (int y = 0; y < 10; ++y) {
            for (int x = 0; x < 10; ++x) {
                if (grid[y][x] == 0) {
                    cnt++;
                    if (cnt == p) { py = y; px = x; break; }
                }
            }
            if (py != -1) break;
        }
        if (py == -1) { // should not happen
            // fallback: find any empty
            for (int y = 0; y < 10; ++y) {
                for (int x = 0; x < 10; ++x) if (grid[y][x] == 0) { py = y; px = x; break; }
                if (py != -1) break;
            }
        }
        if (py != -1) grid[py][px] = f[t];

        long long bestScore = LLONG_MIN;
        vector<int> candidates;
        for (int d = 0; d < 4; ++d) {
            Grid ng = slide(grid, d);
            long long sc = score_grid(ng);
            if (sc > bestScore) {
                bestScore = sc;
                candidates.clear();
                candidates.push_back(d);
            } else if (sc == bestScore) {
                candidates.push_back(d);
            }
        }
        int dir = candidates[0];
        int pref = preferred_dir(f[t]);
        for (int d : candidates) {
            if (d == pref) { dir = d; break; }
        }
        cout << dirc[dir] << '\n' << flush;
        grid = slide(grid, dir);
    }
    return 0;
}