#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 30, W = 30;
    const int N = H * W;
    const double INF = 1e100;

    // Estimated weights
    static double h[H][W - 1]; // horizontal edges (i,j) <-> (i,j+1)
    static double v[H - 1][W]; // vertical edges (i,j) <-> (i+1,j)

    // Usage counts
    static int ch[H][W - 1];
    static int cv[H - 1][W];

    // Initialize weights
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W - 1; j++) {
            h[i][j] = 5000.0;
            ch[i][j] = 0;
        }
    }
    for (int i = 0; i < H - 1; i++) {
        for (int j = 0; j < W; j++) {
            v[i][j] = 5000.0;
            cv[i][j] = 0;
        }
    }

    auto idx = [&](int i, int j) { return i * W + j; };
    auto rev_idx = [&](int id, int &i, int &j) { i = id / W; j = id % W; };

    for (int qi = 0; qi < 1000; qi++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) {
            return 0; // In case of unexpected EOF
        }

        int s = idx(si, sj);
        int t = idx(ti, tj);

        // Dijkstra
        vector<double> dist(N, INF);
        vector<int> prev(N, -1);
        vector<char> prevdir(N, '?');
        priority_queue<pair<double, int>, vector<pair<double, int>>, greater<pair<double, int>>> pq;
        dist[s] = 0.0;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d > dist[u]) continue;
            if (u == t) break;
            int ui, uj;
            rev_idx(u, ui, uj);

            // Up
            if (ui > 0) {
                int vi = ui - 1, vj = uj;
                double w = v[ui - 1][uj];
                int v_id = idx(vi, vj);
                if (dist[v_id] > d + w) {
                    dist[v_id] = d + w;
                    prev[v_id] = u;
                    prevdir[v_id] = 'U';
                    pq.emplace(dist[v_id], v_id);
                }
            }
            // Down
            if (ui + 1 < H) {
                int vi = ui + 1, vj = uj;
                double w = v[ui][uj];
                int v_id = idx(vi, vj);
                if (dist[v_id] > d + w) {
                    dist[v_id] = d + w;
                    prev[v_id] = u;
                    prevdir[v_id] = 'D';
                    pq.emplace(dist[v_id], v_id);
                }
            }
            // Left
            if (uj > 0) {
                int vi = ui, vj = uj - 1;
                double w = h[ui][uj - 1];
                int v_id = idx(vi, vj);
                if (dist[v_id] > d + w) {
                    dist[v_id] = d + w;
                    prev[v_id] = u;
                    prevdir[v_id] = 'L';
                    pq.emplace(dist[v_id], v_id);
                }
            }
            // Right
            if (uj + 1 < W) {
                int vi = ui, vj = uj + 1;
                double w = h[ui][uj];
                int v_id = idx(vi, vj);
                if (dist[v_id] > d + w) {
                    dist[v_id] = d + w;
                    prev[v_id] = u;
                    prevdir[v_id] = 'R';
                    pq.emplace(dist[v_id], v_id);
                }
            }
        }

        // Reconstruct path
        string path;
        {
            int cur = t;
            while (cur != s) {
                char d = prevdir[cur];
                path.push_back(d);
                cur = prev[cur];
            }
            reverse(path.begin(), path.end());
        }

        // Output path and flush
        cout << path << '\n' << flush;

        // Read measured length
        long long measured;
        if (!(cin >> measured)) {
            return 0; // In case of unexpected EOF
        }

        // Compute estimated path length and update weights
        if (!path.empty()) {
            // Calculate predicted length
            double predicted = 0.0;
            int ci = si, cj = sj;

            for (char c : path) {
                if (c == 'U') {
                    predicted += v[ci - 1][cj];
                    ci -= 1;
                } else if (c == 'D') {
                    predicted += v[ci][cj];
                    ci += 1;
                } else if (c == 'L') {
                    predicted += h[ci][cj - 1];
                    cj -= 1;
                } else if (c == 'R') {
                    predicted += h[ci][cj];
                    cj += 1;
                }
            }

            if (predicted <= 0) predicted = 1.0; // safety

            double ratio = (double)measured / predicted;
            double diff = (double)measured - predicted;
            int m = (int)path.size();

            // Update weights along the path
            ci = si; cj = sj;
            for (char c : path) {
                if (c == 'U') {
                    double &ww = v[ci - 1][cj];
                    int &cc = cv[ci - 1][cj];
                    double sf = 1.0 / sqrt((double)cc + 1.0);
                    ww *= (1.0 + 0.5 * (ratio - 1.0) * sf);
                    ww += 0.02 * (diff / m) * sf;
                    if (ww < 1000.0) ww = 1000.0;
                    if (ww > 9000.0) ww = 9000.0;
                    cc++;
                    ci -= 1;
                } else if (c == 'D') {
                    double &ww = v[ci][cj];
                    int &cc = cv[ci][cj];
                    double sf = 1.0 / sqrt((double)cc + 1.0);
                    ww *= (1.0 + 0.5 * (ratio - 1.0) * sf);
                    ww += 0.02 * (diff / m) * sf;
                    if (ww < 1000.0) ww = 1000.0;
                    if (ww > 9000.0) ww = 9000.0;
                    cc++;
                    ci += 1;
                } else if (c == 'L') {
                    double &ww = h[ci][cj - 1];
                    int &cc = ch[ci][cj - 1];
                    double sf = 1.0 / sqrt((double)cc + 1.0);
                    ww *= (1.0 + 0.5 * (ratio - 1.0) * sf);
                    ww += 0.02 * (diff / m) * sf;
                    if (ww < 1000.0) ww = 1000.0;
                    if (ww > 9000.0) ww = 9000.0;
                    cc++;
                    cj -= 1;
                } else if (c == 'R') {
                    double &ww = h[ci][cj];
                    int &cc = ch[ci][cj];
                    double sf = 1.0 / sqrt((double)cc + 1.0);
                    ww *= (1.0 + 0.5 * (ratio - 1.0) * sf);
                    ww += 0.02 * (diff / m) * sf;
                    if (ww < 1000.0) ww = 1000.0;
                    if (ww > 9000.0) ww = 9000.0;
                    cc++;
                    cj += 1;
                }
            }
        } else {
            // No movement; nothing to update
        }
    }

    return 0;
}