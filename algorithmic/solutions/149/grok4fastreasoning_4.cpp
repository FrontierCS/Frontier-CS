#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    const int R = 30, C = 30;
    double h[30][29];
    double v[29][30];
    memset(h, 0, sizeof(h));
    memset(v, 0, sizeof(v));
    for (int i = 0; i < R; i++) for (int j = 0; j < C - 1; j++) h[i][j] = 5000.0;
    for (int i = 0; i < R - 1; i++) for (int j = 0; j < C; j++) v[i][j] = 5000.0;
    auto node = [&](int i, int j) { return i * C + j; };
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        int start = node(si, sj);
        int goal = node(ti, tj);
        // Dijkstra
        vector<double> dist(R * C, 1e100);
        vector<int> prev(R * C, -1);
        dist[start] = 0;
        priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;
        pq.push({0, start});
        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            int ui = u / C, uj = u % C;
            for (int dd = 0; dd < 4; dd++) {
                int vi = ui + dx[dd];
                int vj = uj + dy[dd];
                if (vi < 0 || vi >= R || vj < 0 || vj >= C) continue;
                int vv = node(vi, vj);
                double cost;
                if (dd == 0) { // U
                    cost = v[vi][uj];
                } else if (dd == 1) { // D
                    cost = v[ui][uj];
                } else if (dd == 2) { // L
                    cost = h[ui][vj];
                } else { // R
                    cost = h[ui][uj];
                }
                double nd = d + cost;
                if (nd < dist[vv]) {
                    dist[vv] = nd;
                    prev[vv] = u;
                    pq.push({nd, vv});
                }
            }
        }
        // Reconstruct path
        vector<int> path_nodes;
        int cur = goal;
        while (true) {
            path_nodes.push_back(cur);
            if (cur == start) break;
            cur = prev[cur];
            if (cur == -1) break;
        }
        reverse(path_nodes.begin(), path_nodes.end());
        // Build moves
        string moves = "";
        for (size_t k = 0; k + 1 < path_nodes.size(); k++) {
            int u = path_nodes[k];
            int vv = path_nodes[k + 1];
            int ui = u / C, uj = u % C;
            int vi = vv / C, vj = vv % C;
            char move_c;
            if (vi == ui && vj == uj + 1) {
                move_c = 'R';
            } else if (vi == ui && vj == uj - 1) {
                move_c = 'L';
            } else if (vi == ui - 1 && vj == uj) {
                move_c = 'U';
            } else if (vi == ui + 1 && vj == uj) {
                move_c = 'D';
            } else {
                move_c = '?'; // error
            }
            moves += move_c;
        }
        cout << moves << endl;
        // Read feedback
        int r;
        cin >> r;
        double est_b = (double)r;
        double delta = est_b - dist[goal];
        int num = moves.size();
        if (num == 0) continue;
        double adjust = delta / num;
        // Update edges
        for (size_t k = 0; k + 1 < path_nodes.size(); k++) {
            int u = path_nodes[k];
            int vv = path_nodes[k + 1];
            int ui = u / C, uj = u % C;
            int vi = vv / C, vj = vv % C;
            if (vi == ui && vj == uj + 1) { // R
                h[ui][uj] += adjust;
            } else if (vi == ui && vj == uj - 1) { // L
                h[ui][vj] += adjust;
            } else if (vi == ui - 1 && vj == uj) { // U
                v[vi][uj] += adjust;
            } else if (vi == ui + 1 && vj == uj) { // D
                v[ui][uj] += adjust;
            }
        }
    }
    return 0;
}