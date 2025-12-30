#include <bits/stdc++.h>
using namespace std;

int dx[4] = {-1, 0, 1, 0};
int dy[4] = {0, 1, 0, -1};

void apply_tilt(int g[10][10], char d) {
    if (d == 'F' || d == 'B') {
        for (int c = 0; c < 10; c++) {
            vector<int> lst;
            for (int r = 0; r < 10; r++) if (g[r][c] != 0) lst.push_back(g[r][c]);
            int k = lst.size();
            if (d == 'F') {
                for (int i = 0; i < 10; i++) g[i][c] = (i < k ? lst[i] : 0);
            } else {
                for (int i = 0; i < 10; i++) g[i][c] = (i < 10 - k ? 0 : lst[i - (10 - k)]);
            }
        }
    } else {
        for (int r = 0; r < 10; r++) {
            vector<int> lst;
            for (int c = 0; c < 10; c++) if (g[r][c] != 0) lst.push_back(g[r][c]);
            int k = lst.size();
            if (d == 'L') {
                for (int i = 0; i < 10; i++) g[r][i] = (i < k ? lst[i] : 0);
            } else {
                for (int i = 0; i < 10; i++) g[r][i] = (i < 10 - k ? 0 : lst[i - (10 - k)]);
            }
        }
    }
}

double compute_score(int g[10][10]) {
    int cnt[4] = {0};
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 10; j++) {
            if (g[i][j] != 0) cnt[g[i][j]]++;
        }
    }
    double denom = 0.0;
    for (int i = 1; i <= 3; i++) {
        denom += 1.0 * cnt[i] * cnt[i];
    }
    if (denom == 0.0) return 0.0;
    double num = 0.0;
    for (int fl = 1; fl <= 3; fl++) {
        if (cnt[fl] == 0) continue;
        bool vis[10][10] = {false};
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 10; c++) {
                if (g[r][c] == fl && !vis[r][c]) {
                    int sz = 0;
                    queue<pair<int, int>> q;
                    q.push({r, c});
                    vis[r][c] = true;
                    sz = 1;
                    while (!q.empty()) {
                        auto [x, y] = q.front();
                        q.pop();
                        for (int dir = 0; dir < 4; dir++) {
                            int nx = x + dx[dir];
                            int ny = y + dy[dir];
                            if (nx >= 0 && nx < 10 && ny >= 0 && ny < 10 && g[nx][ny] == fl && !vis[nx][ny]) {
                                vis[nx][ny] = true;
                                q.push({nx, ny});
                                sz++;
                            }
                        }
                    }
                    num += 1.0 * sz * sz;
                }
            }
        }
    }
    return num / denom;
}

int main() {
    vector<int> f(100);
    for (int i = 0; i < 100; i++) {
        cin >> f[i];
    }
    int grid[10][10] = {0};
    for (int t = 0; t < 100; t++) {
        int p;
        cin >> p;
        int er = -1, ec = -1;
        int cnt = 0;
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 10; c++) {
                if (grid[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        er = r;
                        ec = c;
                    }
                }
            }
        }
        grid[er][ec] = f[t];
        if (t == 99) continue;
        double best_sc = -1.0;
        char best_d = ' ';
        int temp[10][10];
        string dirs = "FBLR";
        for (char d : dirs) {
            memcpy(temp, grid, sizeof(int) * 100);
            apply_tilt(temp, d);
            double sc = compute_score(temp);
            if (sc > best_sc) {
                best_sc = sc;
                best_d = d;
            }
        }
        cout << best_d << endl;
        apply_tilt(grid, best_d);
    }
    return 0;
}