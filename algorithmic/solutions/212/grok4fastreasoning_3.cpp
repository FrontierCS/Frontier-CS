#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m, L, R, Sx, Sy, Lq, s;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; i++) {
        cin >> q[i];
    }
    set<int> is_q;
    for (int x : q) is_q.insert(x);
    if (is_q.count(Sx) && (Lq == 0 || Sx != q[0])) {
        cout << "NO" << endl;
        return 0;
    }
    vector<int> p;
    p.push_back(Sx);
    set<int> unvisited;
    for (int i = 1; i <= n; i++) {
        if (i != Sx) unvisited.insert(i);
    }
    int progress = 0;
    if (Lq > 0 && Sx == q[0]) progress = 1;
    int current = Sx;
    while (!unvisited.empty()) {
        vector<int> candidates;
        for (int r : unvisited) {
            if (is_q.count(r) == 0) candidates.push_back(r);
        }
        if (progress < Lq) {
            int nextq = q[progress];
            if (unvisited.count(nextq)) candidates.push_back(nextq);
        }
        if (candidates.empty()) {
            cout << "NO" << endl;
            return 0;
        }
        int best = -1;
        int min_d = INT_MAX;
        for (int r : candidates) {
            int d = abs(r - current);
            if (d < min_d || (d == min_d && r < best)) {
                min_d = d;
                best = r;
            }
        }
        p.push_back(best);
        unvisited.erase(best);
        if (progress < Lq && best == q[progress]) {
            progress++;
        }
        current = best;
    }
    if (progress != Lq || (int)p.size() != n) {
        cout << "NO" << endl;
        return 0;
    }
    // Now build path
    vector<pair<int, int>> path;
    bool vis[41][41] = {false};
    int dx[4] = {-1, 0, 1, 0};
    int dy[4] = {0, 1, 0, -1};
    // First traversal: Sx L to R
    int w = R - L + 1;
    int cur_r = Sx;
    int cur_c = L;
    path.push_back({Sx, L});
    vis[Sx][L] = true;
    for (int c = L + 1; c <= R; c++) {
        path.push_back({Sx, c});
        vis[Sx][c] = true;
    }
    cur_c = R;
    // Now for i=1 to n-1
    for (size_t i = 1; i < p.size(); i++) {
        int nxt_r = p[i];
        pair<int, int> targets[2] = {{nxt_r, L}, {nxt_r, R}};
        int ends[2] = {R, L};
        int best_dist = INT_MAX;
        int best_dir = -1;
        vector<pair<int, int>> best_conn;
        pair<int, int> best_target;
        for (int d = 0; d < 2; d++) {
            int tr = targets[d].first;
            int tc = targets[d].second;
            // BFS
            int dist[41][41];
            memset(dist, -1, sizeof(dist));
            pair<int, int> prev[41][41];
            queue<pair<int, int>> qu;
            qu.push({cur_r, cur_c});
            dist[cur_r][cur_c] = 0;
            bool found = false;
            while (!qu.empty() && !found) {
                auto [r, c] = qu.front();
                qu.pop();
                if (r == tr && c == tc) {
                    found = true;
                    continue;
                }
                for (int dir = 0; dir < 4; dir++) {
                    int nr = r + dx[dir];
                    int nc = c + dy[dir];
                    if (nr < 1 || nr > n || nc < 1 || nc > m) continue;
                    if (vis[nr][nc]) continue;
                    bool is_d = (L <= nc && nc <= R);
                    if (is_d && !(nr == tr && nc == tc)) continue;
                    if (dist[nr][nc] == -1) {
                        dist[nr][nc] = dist[r][c] + 1;
                        prev[nr][nc] = {r, c};
                        qu.push({nr, nc});
                    }
                }
            }
            if (found && dist[tr][tc] < best_dist) {
                best_dist = dist[tr][tc];
                best_dir = d;
                best_target = {tr, tc};
                // reconstruct
                vector<pair<int, int>> conn;
                pair<int, int> at = {tr, tc};
                while (at != make_pair(cur_r, cur_c)) {
                    conn.push_back(at);
                    at = prev[at.first][at.second];
                }
                reverse(conn.begin(), conn.end());
                best_conn = conn;
            }
        }
        if (best_dir == -1) {
            cout << "NO" << endl;
            return 0;
        }
        // add conn
        for (auto cel : best_conn) {
            path.push_back(cel);
            vis[cel.first][cel.second] = true;
        }
        // now traversal rest
        int start_c = best_target.second;
        bool dir_right = (best_dir == 0);
        int step = dir_right ? 1 : -1;
        int next_c = start_c + step;
        int low = dir_right ? L + 1 : L;
        int high = dir_right ? R : R - 1;
        int end_c = ends[best_dir];
        while (next_c >= L && next_c <= R && ((dir_right && next_c <= R) || (!dir_right && next_c >= L))) {
            path.push_back({nxt_r, next_c});
            vis[nxt_r][next_c] = true;
            next_c += step;
        }
        cur_r = nxt_r;
        cur_c = end_c;
    }
    cout << "YES" << endl;
    cout << path.size() << endl;
    for (auto [x, y] : path) {
        cout << x << " " << y << endl;
    }
    return 0;
}