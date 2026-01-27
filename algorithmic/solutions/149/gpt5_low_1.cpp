#include <bits/stdc++.h>
using namespace std;

struct Node {
    double d;
    int v;
    bool operator<(const Node& other) const { return d > other.d; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 30, W = 30, N = H * W;
    // Undirected grid weights
    // Horizontal edges: between (i,j) and (i,j+1) for j in [0..28]
    // Vertical edges: between (i,j) and (i+1,j) for i in [0..28]
    static double wh[H][W - 1];
    static double wv[H - 1][W];

    const double INIT_W = 5000.0;
    for (int i = 0; i < H; i++) for (int j = 0; j < W - 1; j++) wh[i][j] = INIT_W;
    for (int i = 0; i < H - 1; i++) for (int j = 0; j < W; j++) wv[i][j] = INIT_W;

    auto inb = [&](int i, int j) { return (0 <= i && i < H && 0 <= j && j < W); };
    auto id = [&](int i, int j) { return i * W + j; };
    auto fromId = [&](int v){ return pair<int,int>(v / W, v % W); };

    auto get_weight = [&](int i1, int j1, int i2, int j2) -> double {
        if (i1 == i2) {
            // horizontal
            int i = i1;
            if (j2 == j1 + 1) return wh[i][j1];
            else return wh[i][j2];
        } else {
            // vertical
            int j = j1;
            if (i2 == i1 + 1) return wv[i1][j];
            else return wv[i2][j];
        }
    };

    auto get_weight_ref = [&](int i1, int j1, int i2, int j2) -> double& {
        if (i1 == i2) {
            int i = i1;
            if (j2 == j1 + 1) return wh[i][j1];
            else return wh[i][j2]; // j1 == j2+1
        } else {
            int j = j1;
            if (i2 == i1 + 1) return wv[i1][j];
            else return wv[i2][j]; // i1 == i2+1
        }
    };

    const double alpha = 0.2;
    const double MIN_W = 100.0;
    const double MAX_W = 20000.0;

    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        int s = id(si, sj), t = id(ti, tj);

        vector<double> dist(N, 1e100);
        vector<int> prevv(N, -1);
        vector<char> prevmove(N, 0);
        priority_queue<Node> pq;
        dist[s] = 0.0;
        pq.push({0.0, s});

        while (!pq.empty()) {
            auto [cd, v] = pq.top(); pq.pop();
            if (cd > dist[v]) continue;
            if (v == t) break;
            auto [i, j] = fromId(v);
            // Up
            if (i > 0) {
                double w = wv[i - 1][j];
                int u = id(i - 1, j);
                if (dist[u] > cd + w) {
                    dist[u] = cd + w;
                    prevv[u] = v;
                    prevmove[u] = 'U';
                    pq.push({dist[u], u});
                }
            }
            // Down
            if (i + 1 < H) {
                double w = wv[i][j];
                int u = id(i + 1, j);
                if (dist[u] > cd + w) {
                    dist[u] = cd + w;
                    prevv[u] = v;
                    prevmove[u] = 'D';
                    pq.push({dist[u], u});
                }
            }
            // Left
            if (j > 0) {
                double w = wh[i][j - 1];
                int u = id(i, j - 1);
                if (dist[u] > cd + w) {
                    dist[u] = cd + w;
                    prevv[u] = v;
                    prevmove[u] = 'L';
                    pq.push({dist[u], u});
                }
            }
            // Right
            if (j + 1 < W) {
                double w = wh[i][j];
                int u = id(i, j + 1);
                if (dist[u] > cd + w) {
                    dist[u] = cd + w;
                    prevv[u] = v;
                    prevmove[u] = 'R';
                    pq.push({dist[u], u});
                }
            }
        }

        string path;
        {
            int cur = t;
            while (cur != s && cur != -1) {
                path.push_back(prevmove[cur]);
                cur = prevv[cur];
            }
            reverse(path.begin(), path.end());
        }

        if (path.empty()) {
            // Fallback: straight Manhattan path
            int ci = si, cj = sj;
            while (ci < ti) { path.push_back('D'); ci++; }
            while (ci > ti) { path.push_back('U'); ci--; }
            while (cj < tj) { path.push_back('R'); cj++; }
            while (cj > tj) { path.push_back('L'); cj--; }
        }

        cout << path << '\n' << flush;

        long long feedback;
        if (!(cin >> feedback)) return 0;

        // Update weights along the path using multiplicative scaling
        // Scale factor = feedback / estimated_path_weight
        double est = 0.0;
        {
            int ci = si, cj = sj;
            for (char c : path) {
                int ni = ci, nj = cj;
                if (c == 'U') ni--;
                else if (c == 'D') ni++;
                else if (c == 'L') nj--;
                else if (c == 'R') nj++;
                est += get_weight(ci, cj, ni, nj);
                ci = ni; cj = nj;
            }
        }
        if (est <= 0) est = 1.0;
        double factor = (double)feedback / est;

        // Soften scaling by alpha
        double mult = (1.0 - alpha) + alpha * factor;

        {
            int ci = si, cj = sj;
            for (char c : path) {
                int ni = ci, nj = cj;
                if (c == 'U') ni--;
                else if (c == 'D') ni++;
                else if (c == 'L') nj--;
                else if (c == 'R') nj++;
                double& wref = get_weight_ref(ci, cj, ni, nj);
                wref *= mult;
                if (wref < MIN_W) wref = MIN_W;
                if (wref > MAX_W) wref = MAX_W;
                ci = ni; cj = nj;
            }
        }
    }
    return 0;
}