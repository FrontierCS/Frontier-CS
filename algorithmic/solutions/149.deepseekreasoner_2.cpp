#include <bits/stdc++.h>
using namespace std;

const int H = 30, W = 30;
const int QUERIES = 1000;
const double INIT_EST = 5000.0;
const double EXPLORE_C = 1000.0;   // exploration constant
const double MIN_EDGE = 100.0;     // minimum edge cost for Dijkstra

double est_h[H][W-1];      // horizontal edge estimates
double est_v[H-1][W];      // vertical edge estimates
int cnt_h[H][W-1] = {0};   // visitation counts for horizontal edges
int cnt_v[H-1][W] = {0};   // visitation counts for vertical edges

struct EdgeInfo {
    int type;   // 0: horizontal, 1: vertical
    int i, j;   // coordinates of the edge
};

vector<pair<int, EdgeInfo>> adj[H][W];   // adjacency list: neighbor id and edge info

void build_graph() {
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            adj[i][j].clear();
            if (i > 0)    // up
                adj[i][j].push_back({(i-1)*W + j, {1, i-1, j}});
            if (i < H-1)  // down
                adj[i][j].push_back({(i+1)*W + j, {1, i, j}});
            if (j > 0)    // left
                adj[i][j].push_back({i*W + (j-1), {0, i, j-1}});
            if (j < W-1)  // right
                adj[i][j].push_back({i*W + (j+1), {0, i, j}});
        }
    }
}

string dijkstra(int si, int sj, int ti, int tj) {
    int start = si * W + sj;
    int target = ti * W + tj;
    vector<double> dist(H*W, 1e18);
    vector<int> prev(H*W, -1);
    vector<char> prev_move(H*W);
    dist[start] = 0.0;
    priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;
    pq.push({0.0, start});

    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d > dist[u]) continue;
        if (u == target) break;
        int i = u / W, j = u % W;
        for (auto& [v, einfo] : adj[i][j]) {
            double w;
            if (einfo.type == 0) { // horizontal
                double raw = est_h[einfo.i][einfo.j];
                double unc = EXPLORE_C / sqrt(cnt_h[einfo.i][einfo.j] + 1);
                w = max(MIN_EDGE, raw - unc);
            } else { // vertical
                double raw = est_v[einfo.i][einfo.j];
                double unc = EXPLORE_C / sqrt(cnt_v[einfo.i][einfo.j] + 1);
                w = max(MIN_EDGE, raw - unc);
            }
            if (dist[v] > dist[u] + w) {
                dist[v] = dist[u] + w;
                prev[v] = u;
                int ni = v / W, nj = v % W;
                char move;
                if (ni == i-1) move = 'U';
                else if (ni == i+1) move = 'D';
                else if (nj == j-1) move = 'L';
                else move = 'R';
                prev_move[v] = move;
                pq.push({dist[v], v});
            }
        }
    }

    string path = "";
    int cur = target;
    while (cur != start) {
        path += prev_move[cur];
        cur = prev[cur];
    }
    reverse(path.begin(), path.end());
    return path;
}

void update_edges(const string& path, int si, int sj, double observed) {
    int i = si, j = sj;
    double predicted = 0.0;
    vector<tuple<int, int, int>> edges; // type, i, j
    for (char c : path) {
        if (c == 'U') {
            predicted += est_v[i-1][j];
            edges.emplace_back(1, i-1, j);
            i--;
        } else if (c == 'D') {
            predicted += est_v[i][j];
            edges.emplace_back(1, i, j);
            i++;
        } else if (c == 'L') {
            predicted += est_h[i][j-1];
            edges.emplace_back(0, i, j-1);
            j--;
        } else if (c == 'R') {
            predicted += est_h[i][j];
            edges.emplace_back(0, i, j);
            j++;
        }
    }
    if (predicted <= 1e-9) predicted = 1.0;
    double ratio = observed / predicted;
    for (auto& [type, ei, ej] : edges) {
        if (type == 0) { // horizontal
            double sample = est_h[ei][ej] * ratio;
            cnt_h[ei][ej]++;
            est_h[ei][ej] = (est_h[ei][ej] * (cnt_h[ei][ej] - 1) + sample) / cnt_h[ei][ej];
        } else { // vertical
            double sample = est_v[ei][ej] * ratio;
            cnt_v[ei][ej]++;
            est_v[ei][ej] = (est_v[ei][ej] * (cnt_v[ei][ej] - 1) + sample) / cnt_v[ei][ej];
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W-1; ++j)
            est_h[i][j] = INIT_EST;
    for (int i = 0; i < H-1; ++i)
        for (int j = 0; j < W; ++j)
            est_v[i][j] = INIT_EST;

    build_graph();

    int si, sj, ti, tj;
    for (int k = 0; k < QUERIES; ++k) {
        cin >> si >> sj >> ti >> tj;
        string path = dijkstra(si, sj, ti, tj);
        cout << path << endl;
        cout.flush();

        int observed;
        cin >> observed;
        update_edges(path, si, sj, (double)observed);
    }

    return 0;
}