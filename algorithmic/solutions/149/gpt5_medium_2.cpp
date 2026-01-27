#include <bits/stdc++.h>
using namespace std;

struct EdgeRef {
    bool isH; // true for horizontal h[i][j], false for vertical v[i][j]
    int i, j;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 30, W = 30;
    const int N = H * W;
    auto id = [&](int i, int j) { return i * W + j; };
    auto coord = [&](int idv) { return pair<int,int>(idv / W, idv % W); };

    // Initialize estimated weights
    vector<vector<double>> h(H, vector<double>(W - 1, 5000.0));
    vector<vector<double>> v(H - 1, vector<double>(W, 5000.0));

    for (int q = 1; q <= 1000; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        int s = id(si, sj), t = id(ti, tj);

        // Dijkstra
        const double INF = 1e100;
        vector<double> dist(N, INF);
        vector<int> prev(N, -1);
        vector<char> prevc(N, '?');
        priority_queue<pair<double,int>, vector<pair<double,int>>, greater<pair<double,int>>> pq;

        dist[s] = 0.0;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [cd, u] = pq.top(); pq.pop();
            if (cd > dist[u]) continue;
            if (u == t) break;
            auto [ui, uj] = coord(u);
            // Left
            if (uj > 0) {
                int vj = uj - 1, vi = ui;
                int vId = id(vi, vj);
                double w = h[ui][uj - 1];
                if (dist[vId] > cd + w) {
                    dist[vId] = cd + w;
                    prev[vId] = u;
                    prevc[vId] = 'L';
                    pq.emplace(dist[vId], vId);
                }
            }
            // Right
            if (uj + 1 < W) {
                int vj = uj + 1, vi = ui;
                int vId = id(vi, vj);
                double w = h[ui][uj];
                if (dist[vId] > cd + w) {
                    dist[vId] = cd + w;
                    prev[vId] = u;
                    prevc[vId] = 'R';
                    pq.emplace(dist[vId], vId);
                }
            }
            // Up
            if (ui > 0) {
                int vi = ui - 1, vj = uj;
                int vId = id(vi, vj);
                double w = v[ui - 1][uj];
                if (dist[vId] > cd + w) {
                    dist[vId] = cd + w;
                    prev[vId] = u;
                    prevc[vId] = 'U';
                    pq.emplace(dist[vId], vId);
                }
            }
            // Down
            if (ui + 1 < H) {
                int vi = ui + 1, vj = uj;
                int vId = id(vi, vj);
                double w = v[ui][uj];
                if (dist[vId] > cd + w) {
                    dist[vId] = cd + w;
                    prev[vId] = u;
                    prevc[vId] = 'D';
                    pq.emplace(dist[vId], vId);
                }
            }
        }

        // Reconstruct path
        string path_rev;
        int cur = t;
        while (cur != s && cur != -1) {
            path_rev.push_back(prevc[cur]);
            cur = prev[cur];
        }
        string path;
        path.reserve(path_rev.size());
        for (int i = (int)path_rev.size() - 1; i >= 0; --i) path.push_back(path_rev[i]);

        // Output and flush
        cout << path << endl;

        // Read feedback
        int z;
        if (!(cin >> z)) return 0;

        // Update weights along used path via simple SGD
        double Spred = 0.0;
        vector<EdgeRef> used;
        used.reserve(path.size());

        int ci = si, cj = sj;
        for (char c : path) {
            if (c == 'U') {
                // (ci, cj) -> (ci-1, cj) uses v[ci-1][cj]
                Spred += v[ci - 1][cj];
                used.push_back({false, ci - 1, cj});
                ci -= 1;
            } else if (c == 'D') {
                // (ci, cj) -> (ci+1, cj) uses v[ci][cj]
                Spred += v[ci][cj];
                used.push_back({false, ci, cj});
                ci += 1;
            } else if (c == 'L') {
                // (ci, cj) -> (ci, cj-1) uses h[ci][cj-1]
                Spred += h[ci][cj - 1];
                used.push_back({true, ci, cj - 1});
                cj -= 1;
            } else if (c == 'R') {
                // (ci, cj) -> (ci, cj+1) uses h[ci][cj]
                Spred += h[ci][cj];
                used.push_back({true, ci, cj});
                cj += 1;
            }
        }

        int m = (int)used.size();
        if (m > 0) {
            double diff = (double)z - Spred;
            double eta = max(0.05, 0.8 / sqrt((double)q));
            double delta = eta * diff / m;
            for (auto &er : used) {
                if (er.isH) {
                    double &w = h[er.i][er.j];
                    w += delta;
                    if (w < 100.0) w = 100.0;
                    if (w > 10000.0) w = 10000.0;
                } else {
                    double &w = v[er.i][er.j];
                    w += delta;
                    if (w < 100.0) w = 100.0;
                    if (w > 10000.0) w = 10000.0;
                }
            }
        }
    }

    return 0;
}