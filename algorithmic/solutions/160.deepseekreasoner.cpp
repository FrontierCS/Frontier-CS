#include <iostream>
#include <vector>
#include <queue>
#include <array>
using namespace std;

const int N = 10;
using Grid = array<array<int, N>, N>;

const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

Grid tilt(const Grid& g, int dir) {
    Grid res{};
    if (dir == 0) { // F (up)
        for (int j = 0; j < N; ++j) {
            int idx = 0;
            for (int i = 0; i < N; ++i) {
                if (g[i][j] != 0) {
                    res[idx][j] = g[i][j];
                    ++idx;
                }
            }
        }
    } else if (dir == 1) { // B (down)
        for (int j = 0; j < N; ++j) {
            int idx = N - 1;
            for (int i = N - 1; i >= 0; --i) {
                if (g[i][j] != 0) {
                    res[idx][j] = g[i][j];
                    --idx;
                }
            }
        }
    } else if (dir == 2) { // L (left)
        for (int i = 0; i < N; ++i) {
            int idx = 0;
            for (int j = 0; j < N; ++j) {
                if (g[i][j] != 0) {
                    res[i][idx] = g[i][j];
                    ++idx;
                }
            }
        }
    } else { // dir == 3, R (right)
        for (int i = 0; i < N; ++i) {
            int idx = N - 1;
            for (int j = N - 1; j >= 0; --j) {
                if (g[i][j] != 0) {
                    res[i][idx] = g[i][j];
                    --idx;
                }
            }
        }
    }
    return res;
}

int compute_score(const Grid& g) {
    vector<vector<bool>> vis(N, vector<bool>(N, false));
    int score = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (g[i][j] == 0 || vis[i][j]) continue;
            int flavor = g[i][j];
            queue<pair<int, int>> q;
            q.push({i, j});
            vis[i][j] = true;
            int sz = 0;
            while (!q.empty()) {
                auto [x, y] = q.front(); q.pop();
                ++sz;
                for (int d = 0; d < 4; ++d) {
                    int nx = x + dx[d], ny = y + dy[d];
                    if (nx >= 0 && nx < N && ny >= 0 && ny < N && !vis[nx][ny] && g[nx][ny] == flavor) {
                        vis[nx][ny] = true;
                        q.push({nx, ny});
                    }
                }
            }
            score += sz * sz;
        }
    }
    return score;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavors(100);
    for (int i = 0; i < 100; ++i) {
        cin >> flavors[i];
    }

    Grid grid{};
    const string dir_chars = "FBLR";

    for (int t = 0; t < 100; ++t) {
        int p;
        cin >> p;
        int cnt = 0;
        int r = -1, c = -1;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] == 0) {
                    ++cnt;
                    if (cnt == p) {
                        r = i; c = j;
                        break;
                    }
                }
            }
            if (r != -1) break;
        }
        grid[r][c] = flavors[t];

        int best_dir = 0;
        int best_score = -1;
        for (int dir = 0; dir < 4; ++dir) {
            Grid new_grid = tilt(grid, dir);
            int sc = compute_score(new_grid);
            if (sc > best_score) {
                best_score = sc;
                best_dir = dir;
            }
        }

        cout << dir_chars[best_dir] << endl;
        grid = tilt(grid, best_dir);
    }

    return 0;
}