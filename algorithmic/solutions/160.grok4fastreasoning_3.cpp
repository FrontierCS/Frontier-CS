#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> do_tilt(vector<vector<int>> g, char d) {
    if (d == 'F') { // down, increasing row
        for (int j = 0; j < 10; j++) {
            vector<int> cand;
            for (int i = 0; i < 10; i++) if (g[i][j]) cand.push_back(g[i][j]);
            int k = cand.size();
            for (int i = 0; i < 10; i++) g[i][j] = 0;
            for (int i = 0; i < k; i++) g[10 - k + i][j] = cand[i];
        }
    } else if (d == 'B') { // up, decreasing row
        for (int j = 0; j < 10; j++) {
            vector<int> cand;
            for (int i = 0; i < 10; i++) if (g[i][j]) cand.push_back(g[i][j]);
            int k = cand.size();
            for (int i = 0; i < 10; i++) g[i][j] = 0;
            for (int i = 0; i < k; i++) g[i][j] = cand[i];
        }
    } else if (d == 'L') { // left, decreasing col
        for (int i = 0; i < 10; i++) {
            vector<int> cand;
            for (int j = 0; j < 10; j++) if (g[i][j]) cand.push_back(g[i][j]);
            int k = cand.size();
            for (int j = 0; j < 10; j++) g[i][j] = 0;
            for (int j = 0; j < k; j++) g[i][j] = cand[j];
        }
    } else if (d == 'R') { // right, increasing col
        for (int i = 0; i < 10; i++) {
            vector<int> cand;
            for (int j = 0; j < 10; j++) if (g[i][j]) cand.push_back(g[i][j]);
            int k = cand.size();
            for (int j = 0; j < 10; j++) g[i][j] = 0;
            for (int j = 0; j < k; j++) g[i][10 - k + j] = cand[j];
        }
    }
    return g;
}

long long compute_score(const vector<vector<int>>& g) {
    vector<vector<bool>> vis(10, vector<bool>(10, false));
    long long sumsq = 0;
    int dx[4] = {-1, 0, 1, 0};
    int dy[4] = {0, 1, 0, -1};
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 10; j++) {
            if (g[i][j] != 0 && !vis[i][j]) {
                int col = g[i][j];
                int sz = 0;
                queue<pair<int, int>> q;
                q.emplace(i, j);
                vis[i][j] = true;
                while (!q.empty()) {
                    auto [x, y] = q.front(); q.pop();
                    sz++;
                    for (int dir = 0; dir < 4; dir++) {
                        int ni = x + dx[dir];
                        int nj = y + dy[dir];
                        if (ni >= 0 && ni < 10 && nj >= 0 && nj < 10 && !vis[ni][nj] && g[ni][nj] == col) {
                            vis[ni][nj] = true;
                            q.emplace(ni, nj);
                        }
                    }
                }
                sumsq += 1LL * sz * sz;
            }
        }
    }
    return sumsq;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    vector<int> flavors(100);
    for (auto& x : flavors) cin >> x;
    vector<vector<int>> grid(10, vector<int>(10, 0));
    for (int t = 1; t <= 100; t++) {
        int p;
        cin >> p;
        vector<pair<int, int>> empties;
        for (int i = 0; i < 10; i++) {
            for (int j = 0; j < 10; j++) {
                if (grid[i][j] == 0) empties.emplace_back(i, j);
            }
        }
        int r = empties[p - 1].first;
        int c = empties[p - 1].second;
        grid[r][c] = flavors[t - 1];
        if (t == 100) break;
        long long best_score = -1;
        char best_d = ' ';
        for (char d : {'F', 'B', 'L', 'R'}) {
            auto ng = do_tilt(grid, d);
            long long score = compute_score(ng);
            if (score > best_score) {
                best_score = score;
                best_d = d;
            }
        }
        cout << best_d << '\n';
        fflush(stdout);
        grid = do_tilt(grid, best_d);
    }
    return 0;
}