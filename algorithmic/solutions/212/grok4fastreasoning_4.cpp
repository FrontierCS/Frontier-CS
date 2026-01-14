#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m, L, R, Sx, Sy, Lq, s;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    vector<int> q(Lq + 1);
    for (int i = 1; i <= Lq; i++) {
        cin >> q[i];
    }
    int pos = -1;
    for (int i = 1; i <= Lq; i++) {
        if (q[i] == Sx) {
            pos = i;
            break;
        }
    }
    bool possible = true;
    if (pos > 1 && pos != -1) possible = false;
    if (!possible) {
        cout << "NO" << endl;
        return 0;
    }
    vector<int> mand;
    if (pos == 1) {
        for (int i = 2; i <= Lq; i++) mand.push_back(q[i]);
    } else {
        for (int i = 1; i <= Lq; i++) mand.push_back(q[i]);
    }
    set<int> mand_set(mand.begin(), mand.end());
    set<int> frees_set;
    for (int i = 1; i <= n; i++) {
        if (i != Sx && mand_set.find(i) == mand_set.end()) {
            frees_set.insert(i);
        }
    }
    vector<vector<bool>> vis(n + 2, vector<bool>(m + 2, false));
    vector<pair<int, int>> path;
    // Add starting block
    for (int y = L; y <= R; y++) {
        path.push_back({Sx, y});
        vis[Sx][y] = true;
    }
    int cur_x = Sx;
    int cur_y = R;
    vector<int> order;
    order.push_back(Sx);
    set<int> processed;
    processed.insert(Sx);
    int mand_idx = 0;
    possible = true;
    while (order.size() < (size_t)n) {
        vector<int> candidates;
        if (mand_idx < (int)mand.size()) {
            int next_r = mand[mand_idx];
            if (processed.find(next_r) == processed.end()) {
                candidates.push_back(next_r);
            }
        }
        for (int r : frees_set) {
            if (processed.find(r) == processed.end()) {
                candidates.push_back(r);
            }
        }
        if (candidates.empty()) {
            possible = false;
            break;
        }
        int next_pos = order.size() + 1;
        bool is_odd = (next_pos % 2 == 1);
        int entry_y_base = is_odd ? L : R;
        int min_extra = INT_MAX;
        int best_cand = -1;
        int best_diff = INT_MAX;
        for (int cand : candidates) {
            int tx = cand;
            int ty = is_odd ? L : R;
            // BFS to compute dist
            vector<vector<int>> dist(n + 2, vector<int>(m + 2, -1));
            vector<vector<pair<int, int>>> parent(n + 2, vector<pair<int, int>>(m + 2, {-1, -1}));
            queue<pair<int, int>> qq;
            dist[cur_x][cur_y] = 0;
            qq.push({cur_x, cur_y});
            bool reached = false;
            while (!qq.empty() && !reached) {
                auto [x, y] = qq.front();
                qq.pop();
                if (x == tx && y == ty) {
                    reached = true;
                    break;
                }
                int dx[4] = {-1, 0, 1, 0};
                int dy[4] = {0, 1, 0, -1};
                for (int d = 0; d < 4; d++) {
                    int nx = x + dx[d];
                    int ny = y + dy[d];
                    if (nx >= 1 && nx <= n && ny >= 1 && ny <= m && dist[nx][ny] == -1 &&
                        !vis[nx][ny] && (ny < L || ny > R || (nx == tx && ny == ty))) {
                        dist[nx][ny] = dist[x][y] + 1;
                        parent[nx][ny] = {x, y};
                        qq.push({nx, ny});
                        if (nx == tx && ny == ty) {
                            reached = true;
                        }
                    }
                }
            }
            int this_dist = dist[tx][ty];
            int this_extra = (this_dist == -1) ? INT_MAX : this_dist - 1;
            int this_diff = abs(cand - cur_x);
            if (this_extra < min_extra ||
                (this_extra == min_extra && this_diff < best_diff) ||
                (this_extra == min_extra && this_diff == best_diff && cand < best_cand)) {
                min_extra = this_extra;
                best_diff = this_diff;
                best_cand = cand;
            }
        }
        if (min_extra == INT_MAX) {
            possible = false;
            break;
        }
        // Now build path for best_cand
        int tx = best_cand;
        int ty = is_odd ? L : R;
        // BFS again with parent
        vector<vector<int>> dist(n + 2, vector<int>(m + 2, -1));
        vector<vector<pair<int, int>>> parent(n + 2, vector<pair<int, int>>(m + 2, {-1, -1}));
        queue<pair<int, int>> qq;
        dist[cur_x][cur_y] = 0;
        qq.push({cur_x, cur_y});
        while (!qq.empty()) {
            auto [x, y] = qq.front();
            qq.pop();
            if (x == tx && y == ty) break;
            int dx[4] = {-1, 0, 1, 0};
            int dy[4] = {0, 1, 0, -1};
            for (int d = 0; d < 4; d++) {
                int nx = x + dx[d];
                int ny = y + dy[d];
                if (nx >= 1 && nx <= n && ny >= 1 && ny <= m && dist[nx][ny] == -1 &&
                    !vis[nx][ny] && (ny < L || ny > R || (nx == tx && ny == ty))) {
                    dist[nx][ny] = dist[x][y] + 1;
                    parent[nx][ny] = {x, y};
                    qq.push({nx, ny});
                }
            }
        }
        // Reconstruct
        vector<pair<int, int>> subpath;
        pair<int, int> at = {tx, ty};
        while (at != make_pair(cur_x, cur_y)) {
            subpath.push_back(at);
            at = parent[at.first][at.second];
        }
        subpath.push_back({cur_x, cur_y});
        reverse(subpath.begin(), subpath.end());
        // Add intermediates
        for (size_t i = 1; i + 1 < subpath.size(); ++i) {  // up to before target
            auto [xx, yy] = subpath[i];
            path.push_back({xx, yy});
            vis[xx][yy] = true;
        }
        // Add target
        path.push_back({tx, ty});
        vis[tx][ty] = true;
        cur_x = tx;
        cur_y = ty;
        // Add rest of block
        int step = is_odd ? 1 : -1;
        int start_y = ty;
        for (int y = ty + step;; y += step) {
            if ((is_odd && y > R) || (!is_odd && y < L)) break;
            path.push_back({tx, y});
            vis[tx][y] = true;
            cur_x = tx;
            cur_y = y;
        }
        // Add to order
        order.push_back(best_cand);
        processed.insert(best_cand);
        if (mand_idx < (int)mand.size() && best_cand == mand[mand_idx]) {
            mand_idx++;
        }
    }
    if (!possible || order.size() != (size_t)n || mand_idx != (int)mand.size()) {
        cout << "NO" << endl;
    } else {
        cout << "YES" << endl;
        cout << path.size() << endl;
        for (auto [x, y] : path) {
            cout << x << " " << y << endl;
        }
    }
    return 0;
}