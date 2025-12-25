#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>
#include <string>
#include <cstring>

using namespace std;

const double INF = 1e18;
const double INIT_EST = 5000.0;
const double MIN_EST = 100.0;
const double MAX_EST = 20000.0;

int main() {
    double h_est[30][29];
    double v_est[29][30];
    int h_count[30][29] = {0};
    int v_count[29][30] = {0};

    for (int i = 0; i < 30; ++i)
        for (int j = 0; j < 29; ++j)
            h_est[i][j] = INIT_EST;
    for (int i = 0; i < 29; ++i)
        for (int j = 0; j < 30; ++j)
            v_est[i][j] = INIT_EST;

    int si, sj, ti, tj;
    for (int q = 0; q < 1000; ++q) {
        cin >> si >> sj >> ti >> tj;

        // Dijkstra
        vector<vector<double>> dist(30, vector<double>(30, INF));
        vector<vector<char>> prev_dir(30, vector<char>(30, 0));
        using Node = pair<double, pair<int, int>>;
        priority_queue<Node, vector<Node>, greater<Node>> pq;
        dist[si][sj] = 0.0;
        pq.push({0.0, {si, sj}});

        while (!pq.empty()) {
            auto [d, pos] = pq.top(); pq.pop();
            int i = pos.first, j = pos.second;
            if (d > dist[i][j]) continue;
            if (i == ti && j == tj) break;

            // up
            if (i > 0) {
                int ni = i - 1, nj = j;
                double w = v_est[i - 1][j];
                if (dist[ni][nj] > d + w) {
                    dist[ni][nj] = d + w;
                    prev_dir[ni][nj] = 'U';
                    pq.push({dist[ni][nj], {ni, nj}});
                }
            }
            // down
            if (i < 29) {
                int ni = i + 1, nj = j;
                double w = v_est[i][j];
                if (dist[ni][nj] > d + w) {
                    dist[ni][nj] = d + w;
                    prev_dir[ni][nj] = 'D';
                    pq.push({dist[ni][nj], {ni, nj}});
                }
            }
            // left
            if (j > 0) {
                int ni = i, nj = j - 1;
                double w = h_est[i][j - 1];
                if (dist[ni][nj] > d + w) {
                    dist[ni][nj] = d + w;
                    prev_dir[ni][nj] = 'L';
                    pq.push({dist[ni][nj], {ni, nj}});
                }
            }
            // right
            if (j < 29) {
                int ni = i, nj = j + 1;
                double w = h_est[i][j];
                if (dist[ni][nj] > d + w) {
                    dist[ni][nj] = d + w;
                    prev_dir[ni][nj] = 'R';
                    pq.push({dist[ni][nj], {ni, nj}});
                }
            }
        }

        // Reconstruct path and collect edges
        string path = "";
        vector<pair<bool, pair<int, int>>> edges; // (is_horizontal, (i, j))
        int i = ti, j = tj;
        while (!(i == si && j == sj)) {
            char dir = prev_dir[i][j];
            path += dir;
            if (dir == 'U') {
                edges.push_back({false, {i - 1, j}});
                i = i - 1;
            } else if (dir == 'D') {
                edges.push_back({false, {i, j}});
                i = i + 1;
            } else if (dir == 'L') {
                edges.push_back({true, {i, j - 1}});
                j = j - 1;
            } else if (dir == 'R') {
                edges.push_back({true, {i, j}});
                j = j + 1;
            }
        }
        reverse(path.begin(), path.end());
        reverse(edges.begin(), edges.end());

        cout << path << endl;
        cout.flush();

        // Read observed length
        int L;
        cin >> L;

        // Compute predicted length
        double pred = 0.0;
        for (auto &e : edges) {
            if (e.first)
                pred += h_est[e.second.first][e.second.second];
            else
                pred += v_est[e.second.first][e.second.second];
        }
        double error = L - pred;
        int len = edges.size();

        // Update estimates for edges on the path
        for (auto &e : edges) {
            int i = e.second.first, j = e.second.second;
            if (e.first) { // horizontal
                int cnt = ++h_count[i][j];
                double lr = 0.5 / (1.0 + sqrt(cnt));
                h_est[i][j] += (error / len) * lr;
                if (h_est[i][j] < MIN_EST) h_est[i][j] = MIN_EST;
                if (h_est[i][j] > MAX_EST) h_est[i][j] = MAX_EST;
            } else { // vertical
                int cnt = ++v_count[i][j];
                double lr = 0.5 / (1.0 + sqrt(cnt));
                v_est[i][j] += (error / len) * lr;
                if (v_est[i][j] < MIN_EST) v_est[i][j] = MIN_EST;
                if (v_est[i][j] > MAX_EST) v_est[i][j] = MAX_EST;
            }
        }
    }
    return 0;
}