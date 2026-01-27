#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    double dist;
    bool operator<(const Node& other) const {
        return dist > other.dist;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 30, W = 30, N = H * W;
    const double MINW = 1000.0, MAXW = 9000.0;

    vector<double> hRow(H, 5000.0), vCol(W, 5000.0);

    auto inb = [&](int i, int j){ return 0 <= i && i < H && 0 <= j && j < W; };
    auto id = [&](int i, int j){ return i*W + j; };
    auto coord = [&](int idv){ return pair<int,int>(idv / W, idv % W); };

    int si, sj, ti, tj;
    for (int q = 0; q < 1000; q++) {
        if (!(cin >> si >> sj >> ti >> tj)) break;

        int s = id(si, sj), t = id(ti, tj);

        // Dijkstra
        const double INF = 1e100;
        vector<double> dist(N, INF);
        vector<int> prev(N, -1);
        priority_queue<Node> pq;
        dist[s] = 0.0;
        pq.push({s, 0.0});

        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            if (cur.dist != dist[cur.id]) continue;
            if (cur.id == t) break;
            auto [i, j] = coord(cur.id);

            // neighbors
            // Up
            if (i > 0) {
                int nid = id(i-1, j);
                double w = vCol[j];
                if (dist[nid] > dist[cur.id] + w) {
                    dist[nid] = dist[cur.id] + w;
                    prev[nid] = cur.id;
                    pq.push({nid, dist[nid]});
                }
            }
            // Down
            if (i < H-1) {
                int nid = id(i+1, j);
                double w = vCol[j];
                if (dist[nid] > dist[cur.id] + w) {
                    dist[nid] = dist[cur.id] + w;
                    prev[nid] = cur.id;
                    pq.push({nid, dist[nid]});
                }
            }
            // Left
            if (j > 0) {
                int nid = id(i, j-1);
                double w = hRow[i];
                if (dist[nid] > dist[cur.id] + w) {
                    dist[nid] = dist[cur.id] + w;
                    prev[nid] = cur.id;
                    pq.push({nid, dist[nid]});
                }
            }
            // Right
            if (j < W-1) {
                int nid = id(i, j+1);
                double w = hRow[i];
                if (dist[nid] > dist[cur.id] + w) {
                    dist[nid] = dist[cur.id] + w;
                    prev[nid] = cur.id;
                    pq.push({nid, dist[nid]});
                }
            }
        }

        // Reconstruct path
        vector<int> path_nodes;
        for (int v = t; v != -1; v = prev[v]) path_nodes.push_back(v);
        reverse(path_nodes.begin(), path_nodes.end());

        string path;
        path.reserve(path_nodes.size());
        vector<int> hcnt(H, 0), vcnt(W, 0);
        for (size_t k = 1; k < path_nodes.size(); k++) {
            int u = path_nodes[k-1], v = path_nodes[k];
            int du = v - u;
            if (du == 1) {
                path.push_back('R');
                auto [ui, uj] = coord(u);
                hcnt[ui]++;
            } else if (du == -1) {
                path.push_back('L');
                auto [ui, uj] = coord(u);
                hcnt[ui]++;
            } else if (du == W) {
                path.push_back('D');
                auto [ui, uj] = coord(u);
                vcnt[uj]++;
            } else if (du == -W) {
                path.push_back('U');
                auto [ui, uj] = coord(u);
                vcnt[uj]++;
            }
        }

        cout << path << endl;

        long long observed;
        if (!(cin >> observed)) break;

        // Update estimates via simple SGD
        double pred = 0.0;
        int L = 0;
        for (int i = 0; i < H; i++) {
            pred += hcnt[i] * hRow[i];
            L += hcnt[i];
        }
        for (int j = 0; j < W; j++) {
            pred += vcnt[j] * vCol[j];
            L += vcnt[j];
        }

        if (L > 0) {
            double diff = (double)observed - pred;
            double alpha = 0.3 * (1.0 - (double)q / 1200.0);
            if (alpha < 0.05) alpha = 0.05;
            double step = alpha * diff / (double)L;

            for (int i = 0; i < H; i++) {
                if (hcnt[i]) {
                    hRow[i] += step * hcnt[i];
                    if (hRow[i] < MINW) hRow[i] = MINW;
                    if (hRow[i] > MAXW) hRow[i] = MAXW;
                }
            }
            for (int j = 0; j < W; j++) {
                if (vcnt[j]) {
                    vCol[j] += step * vcnt[j];
                    if (vCol[j] < MINW) vCol[j] = MINW;
                    if (vCol[j] > MAXW) vCol[j] = MAXW;
                }
            }
        }
    }
    return 0;
}