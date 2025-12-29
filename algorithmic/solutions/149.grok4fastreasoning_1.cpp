#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<double> ch(30, 5000.0);
    vector<double> cv(30, 5000.0);
    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        vector<vector<double>> dist(30, vector<double>(30, 1e18));
        dist[si][sj] = 0;
        using T = tuple<double, int, int>;
        priority_queue<T, vector<T>, greater<T>> pq;
        pq.emplace(0, si, sj);
        vector<vector<pair<int, int>>> pre(30, vector<pair<int, int>>(30, {-1, -1}));
        while (!pq.empty()) {
            auto [d, x, y] = pq.top(); pq.pop();
            if (d > dist[x][y]) continue;
            if (x > 0) {
                int nx = x - 1, ny = y;
                double cost = cv[y];
                if (dist[nx][ny] > dist[x][y] + cost) {
                    dist[nx][ny] = dist[x][y] + cost;
                    pre[nx][ny] = {x, y};
                    pq.emplace(dist[nx][ny], nx, ny);
                }
            }
            if (x < 29) {
                int nx = x + 1, ny = y;
                double cost = cv[y];
                if (dist[nx][ny] > dist[x][y] + cost) {
                    dist[nx][ny] = dist[x][y] + cost;
                    pre[nx][ny] = {x, y};
                    pq.emplace(dist[nx][ny], nx, ny);
                }
            }
            if (y > 0) {
                int nx = x, ny = y - 1;
                double cost = ch[x];
                if (dist[nx][ny] > dist[x][y] + cost) {
                    dist[nx][ny] = dist[x][y] + cost;
                    pre[nx][ny] = {x, y};
                    pq.emplace(dist[nx][ny], nx, ny);
                }
            }
            if (y < 29) {
                int nx = x, ny = y + 1;
                double cost = ch[x];
                if (dist[nx][ny] > dist[x][y] + cost) {
                    dist[nx][ny] = dist[x][y] + cost;
                    pre[nx][ny] = {x, y};
                    pq.emplace(dist[nx][ny], nx, ny);
                }
            }
        }
        vector<pair<int, int>> path_pos;
        pair<int, int> cur = {ti, tj};
        bool reachable = true;
        while (true) {
            path_pos.push_back(cur);
            if (cur.first == si && cur.second == sj) break;
            cur = pre[cur.first][cur.second];
            if (cur.first == -1) {
                reachable = false;
                break;
            }
        }
        if (!reachable) {
            // Fallback to a simple Manhattan path
            string fallback;
            int dx = ti - si;
            int dy = tj - sj;
            int abs_dx = abs(dx);
            int abs_dy = abs(dy);
            char vert = (dx > 0) ? 'D' : 'U';
            char hor = (dy > 0) ? 'R' : 'L';
            for (int i = 0; i < abs_dx; i++) fallback += vert;
            for (int i = 0; i < abs_dy; i++) fallback += hor;
            cout << fallback << endl << flush;
            int dummy;
            cin >> dummy;
            continue;
        }
        reverse(path_pos.begin(), path_pos.end());
        string moves;
        for (size_t i = 0; i + 1 < path_pos.size(); ++i) {
            int x1 = path_pos[i].first, y1 = path_pos[i].second;
            int x2 = path_pos[i + 1].first, y2 = path_pos[i + 1].second;
            int dx_ = x2 - x1;
            int dy_ = y2 - y1;
            if (dx_ == 0 && dy_ == 1) moves += 'R';
            else if (dx_ == 0 && dy_ == -1) moves += 'L';
            else if (dx_ == 1 && dy_ == 0) moves += 'D';
            else if (dx_ == -1 && dy_ == 0) moves += 'U';
        }
        vector<int> num_h(30, 0);
        vector<int> num_v(30, 0);
        for (size_t i = 0; i + 1 < path_pos.size(); ++i) {
            int x1 = path_pos[i].first, y1 = path_pos[i].second;
            int x2 = path_pos[i + 1].first, y2 = path_pos[i + 1].second;
            if (x1 == x2) {
                num_h[x1]++;
            } else {
                num_v[y1]++;
            }
        }
        cout << moves << endl << flush;
        int observed;
        cin >> observed;
        double est_sum = dist[ti][tj];
        if (est_sum < 1e17 && observed > 0) {
            double factor = (double)observed / est_sum;
            for (int i = 0; i < 30; i++) {
                if (num_h[i] > 0) ch[i] *= factor;
            }
            for (int j = 0; j < 30; j++) {
                if (num_v[j] > 0) cv[j] *= factor;
            }
        }
    }
    return 0;
}