#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 30;
    int NN = N * N;
    vector<vector<double>> horiz(N, vector<double>(N - 1, 5000.0));
    vector<vector<double>> vert(N - 1, vector<double>(N, 5000.0));
    double lr = 0.05;
    double minw = 1000.0;
    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        int start = si * N + sj;
        int goal = ti * N + tj;
        vector<double> dist(NN, 1e18);
        vector<int> par(NN, -1);
        dist[start] = 0;
        priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;
        pq.push({0, start});
        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            int i = u / N, j = u % N;
            if (j > 0) {
                int v = i * N + j - 1;
                double w = horiz[i][j - 1];
                if (dist[v] > dist[u] + w) {
                    dist[v] = dist[u] + w;
                    par[v] = u;
                    pq.push({dist[v], v});
                }
            }
            if (j < N - 1) {
                int v = i * N + j + 1;
                double w = horiz[i][j];
                if (dist[v] > dist[u] + w) {
                    dist[v] = dist[u] + w;
                    par[v] = u;
                    pq.push({dist[v], v});
                }
            }
            if (i > 0) {
                int v = (i - 1) * N + j;
                double w = vert[i - 1][j];
                if (dist[v] > dist[u] + w) {
                    dist[v] = dist[u] + w;
                    par[v] = u;
                    pq.push({dist[v], v});
                }
            }
            if (i < N - 1) {
                int v = (i + 1) * N + j;
                double w = vert[i][j];
                if (dist[v] > dist[u] + w) {
                    dist[v] = dist[u] + w;
                    par[v] = u;
                    pq.push({dist[v], v});
                }
            }
        }
        vector<int> path_nodes;
        int cur = goal;
        while (cur != -1) {
            path_nodes.push_back(cur);
            cur = par[cur];
        }
        reverse(path_nodes.begin(), path_nodes.end());
        string moves;
        for (size_t k = 0; k + 1 < path_nodes.size(); k++) {
            int u = path_nodes[k], v = path_nodes[k + 1];
            int iu = u / N, ju = u % N;
            int iv = v / N, jv = v % N;
            if (iu == iv) {
                if (jv == ju + 1) moves += 'R';
                else if (jv == ju - 1) moves += 'L';
            } else if (ju == jv) {
                if (iv == iu + 1) moves += 'D';
                else if (iv == iu - 1) moves += 'U';
            }
        }
        cout << moves << endl;
        cout.flush();
        int fk;
        cin >> fk;
        double predicted = dist[goal];
        double error = fk - predicted;
        int num_steps = moves.size();
        if (num_steps == 0) continue;
        double delta = lr * error / num_steps;
        for (size_t k = 0; k + 1 < path_nodes.size(); k++) {
            int u = path_nodes[k], v = path_nodes[k + 1];
            int iu = u / N, ju = u % N;
            int iv = v / N, jv = v % N;
            if (iu == iv) {
                int jj = min(ju, jv);
                horiz[iu][jj] += delta;
                if (horiz[iu][jj] < minw) horiz[iu][jj] = minw;
            } else {
                int ii = min(iu, iv);
                vert[ii][ju] += delta;
                if (vert[ii][ju] < minw) vert[ii][ju] = minw;
            }
        }
    }
    return 0;
}