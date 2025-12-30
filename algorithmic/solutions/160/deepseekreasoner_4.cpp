#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

const int N = 10;
const int dr[4] = {-1, 1, 0, 0};
const int dc[4] = {0, 0, -1, 1};

struct Eval {
    int main_score;
    long long potential;
    bool operator<(const Eval& other) const {
        if (main_score != other.main_score) return main_score < other.main_score;
        return potential < other.potential;
    }
};

// tilt functions
void tilt_forward(const vector<vector<int>>& src, vector<vector<int>>& dst) {
    for (int c = 0; c < N; ++c) {
        int idx = 0;
        for (int r = 0; r < N; ++r) {
            if (src[r][c] != 0) {
                dst[idx][c] = src[r][c];
                ++idx;
            }
        }
        while (idx < N) dst[idx++][c] = 0;
    }
}

void tilt_backward(const vector<vector<int>>& src, vector<vector<int>>& dst) {
    for (int c = 0; c < N; ++c) {
        int idx = N - 1;
        for (int r = N - 1; r >= 0; --r) {
            if (src[r][c] != 0) {
                dst[idx][c] = src[r][c];
                --idx;
            }
        }
        while (idx >= 0) dst[idx--][c] = 0;
    }
}

void tilt_left(const vector<vector<int>>& src, vector<vector<int>>& dst) {
    for (int r = 0; r < N; ++r) {
        int idx = 0;
        for (int c = 0; c < N; ++c) {
            if (src[r][c] != 0) {
                dst[r][idx] = src[r][c];
                ++idx;
            }
        }
        while (idx < N) dst[r][idx++] = 0;
    }
}

void tilt_right(const vector<vector<int>>& src, vector<vector<int>>& dst) {
    for (int r = 0; r < N; ++r) {
        int idx = N - 1;
        for (int c = N - 1; c >= 0; --c) {
            if (src[r][c] != 0) {
                dst[r][idx] = src[r][c];
                --idx;
            }
        }
        while (idx >= 0) dst[r][idx--] = 0;
    }
}

void apply_tilt(const vector<vector<int>>& src, vector<vector<int>>& dst, char dir) {
    if (dir == 'F') tilt_forward(src, dst);
    else if (dir == 'B') tilt_backward(src, dst);
    else if (dir == 'L') tilt_left(src, dst);
    else if (dir == 'R') tilt_right(src, dst);
}

// compute sum of squares of connected components
int compute_score(const vector<vector<int>>& g) {
    vector<vector<bool>> vis(N, vector<bool>(N, false));
    int total = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (g[i][j] != 0 && !vis[i][j]) {
                int flavor = g[i][j];
                int size = 0;
                queue<pair<int, int>> q;
                q.push({i, j});
                vis[i][j] = true;
                while (!q.empty()) {
                    auto [r, c] = q.front(); q.pop();
                    ++size;
                    for (int d = 0; d < 4; ++d) {
                        int nr = r + dr[d];
                        int nc = c + dc[d];
                        if (nr >= 0 && nr < N && nc >= 0 && nc < N &&
                            !vis[nr][nc] && g[nr][nc] == flavor) {
                            vis[nr][nc] = true;
                            q.push({nr, nc});
                        }
                    }
                }
                total += size * size;
            }
        }
    }
    return total;
}

// compute potential future connections
long long compute_potential(const vector<vector<int>>& g, const vector<int>& rem) {
    vector<int> cnt_adj(4, 0); // for flavors 1,2,3
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (g[i][j] == 0) {
                bool has[4] = {false, false, false, false};
                for (int d = 0; d < 4; ++d) {
                    int ni = i + dr[d];
                    int nj = j + dc[d];
                    if (ni >= 0 && ni < N && nj >= 0 && nj < N && g[ni][nj] != 0) {
                        has[g[ni][nj]] = true;
                    }
                }
                for (int fl = 1; fl <= 3; ++fl) {
                    if (has[fl]) cnt_adj[fl]++;
                }
            }
        }
    }
    long long pot = 0;
    for (int fl = 1; fl <= 3; ++fl) {
        pot += (long long)rem[fl] * cnt_adj[fl];
    }
    return pot;
}

int main() {
    // read flavors
    vector<int> f(100);
    for (int i = 0; i < 100; ++i) cin >> f[i];

    // remaining counts per flavor
    vector<int> rem(4, 0);
    for (int fl : f) rem[fl]++;

    // initial empty grid
    vector<vector<int>> grid(N, vector<int>(N, 0));
    vector<vector<int>> tmp(N, vector<int>(N));

    // directions in tie-breaking order
    vector<char> dirs = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; ++t) {
        int p;
        cin >> p;  // 1-indexed empty cell index

        // decrement remaining count for current candy
        int flavor = f[t];
        rem[flavor]--;

        // find the p-th empty cell
        int cnt = 0;
        int row = -1, col = -1;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] == 0) {
                    ++cnt;
                    if (cnt == p) {
                        row = i;
                        col = j;
                        break;
                    }
                }
            }
            if (row != -1) break;
        }
        // place the candy
        grid[row][col] = flavor;

        // evaluate each tilt direction
        Eval best = {-1, -1};
        char best_dir = 'F';
        for (char dir : dirs) {
            apply_tilt(grid, tmp, dir);
            int main_score = compute_score(tmp);
            long long potential = compute_potential(tmp, rem);
            Eval cur = {main_score, potential};
            if (best < cur) {
                best = cur;
                best_dir = dir;
            }
        }

        // apply the chosen tilt
        apply_tilt(grid, tmp, best_dir);
        grid = tmp;

        // output direction
        cout << best_dir << endl;
        cout.flush();
    }
    return 0;
}