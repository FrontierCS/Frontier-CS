#include <bits/stdc++.h>
using namespace std;

int dx[4] = {-1, 0, 1, 0};
int dy[4] = {0, 1, 0, -1};

pair<int, vector<pair<int, int>>> get_conn(int sx, int sy, int tx, int ty, unsigned long long mask, bool vis[41][41], int n, int m, int L, int R) {
    int dist[41][41];
    memset(dist, -1, sizeof(dist));
    pair<int, int> parent[41][41];
    queue<pair<int, int>> q;
    q.push({sx, sy});
    dist[sx][sy] = 0;
    bool reached = false;
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        if (x == tx && y == ty) {
            reached = true;
            break;
        }
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (nx < 1 || nx > n || ny < 1 || ny > m) continue;
            if (dist[nx][ny] != -1) continue;
            bool is_forbidden = ((mask & (1ULL << (nx - 1))) == 0) && (L <= ny && ny <= R) && !(nx == tx && ny == ty);
            if (is_forbidden || vis[nx][ny]) continue;
            dist[nx][ny] = dist[x][y] + 1;
            parent[nx][ny] = {x, y};
            q.push({nx, ny});
        }
    }
    if (!reached) return {-1, {}};
    vector<pair<int, int>> pth;
    pair<int, int> at = {tx, ty};
    while (true) {
        pth.push_back(at);
        if (at.first == sx && at.second == sy) break;
        at = parent[at.first][at.second];
    }
    reverse(pth.begin(), pth.end());
    return {dist[tx][ty], pth};
}

int main() {
    int n, m, L, R, Sx, Sy, Lq, s;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    vector<int> Q(Lq + 1);
    for (int i = 1; i <= Lq; i++) cin >> Q[i];
    vector<vector<int>> orders(2);
    // down first
    for (int r = Sx; r <= n; r++) orders[0].push_back(r);
    for (int r = 1; r < Sx; r++) orders[0].push_back(r);
    // up first
    for (int r = Sx; r >= 1; r--) orders[1].push_back(r);
    for (int r = Sx + 1; r <= n; r++) orders[1].push_back(r);
    pair<vector<pair<int, int>>, int> best_sol = {{}, INT_MAX};
    int w = R - L + 1;
    for (int oi = 0; oi < 2; oi++) {
        vector<int> p = orders[oi];
        // check subsequence
        int j = 0;
        for (int r : p) {
            if (j < Lq && r == Q[j + 1]) j++;
        }
        if (j < Lq) continue;
        // build path
        vector<pair<int, int>> this_path;
        bool this_vis[41][41] = {false};
        unsigned long long this_mask = 0;
        // initial block
        this_path.push_back({Sx, L});
        this_vis[Sx][L] = true;
        for (int c = L + 1; c <= R; c++) {
            this_path.push_back({Sx, c});
            this_vis[Sx][c] = true;
        }
        this_mask |= (1ULL << (Sx - 1));
        int curr_x = Sx, curr_y = R;
        bool success = true;
        for (size_t ii = 1; ii < p.size(); ii++) {
            int r = p[ii];
            int best_d = INT_MAX;
            vector<pair<int, int>> best_conn;
            int best_dir = -1;
            for (int dir = 0; dir < 2; dir++) {
                int sc = (dir == 0 ? L : R);
                auto [d, pth] = get_conn(curr_x, curr_y, r, sc, this_mask, this_vis, n, m, L, R);
                if (d != -1 && d < best_d) {
                    best_d = d;
                    best_conn = pth;
                    best_dir = dir;
                }
            }
            if (best_d == INT_MAX) {
                success = false;
                break;
            }
            // add connection new cells
            for (size_t k = 1; k < best_conn.size(); k++) {
                this_path.push_back(best_conn[k]);
                int xx = best_conn[k].first, yy = best_conn[k].second;
                this_vis[xx][yy] = true;
            }
            // add block rest
            int sc = (best_dir == 0 ? L : R);
            int col = sc;
            int step = (best_dir == 0 ? 1 : -1);
            for (int k = 1; k < w; k++) {
                col += step;
                this_path.push_back({r, col});
                this_vis[r][col] = true;
            }
            this_mask |= (1ULL << (r - 1));
            curr_x = r;
            curr_y = (best_dir == 0 ? R : L);
        }
        if (success) {
            int this_cnt = this_path.size();
            if (this_cnt < best_sol.second) {
                best_sol = {this_path, this_cnt};
            }
        }
    }
    if (best_sol.second == INT_MAX) {
        cout << "NO" << endl;
    } else {
        cout << "YES" << endl;
        cout << best_sol.second << endl;
        for (auto pr : best_sol.first) {
            cout << pr.first << " " << pr.second << endl;
        }
    }
    return 0;
}