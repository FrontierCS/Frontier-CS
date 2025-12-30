#include <bits/stdc++.h>
using namespace std;

struct Solver {
    static constexpr int H = 30;
    static constexpr int W = 30;
    static constexpr int N = H * W;

    vector<double> rowW, colW;

    Solver() {
        rowW.assign(H, 5000.0);
        colW.assign(W, 5000.0);
    }

    inline int id(int i, int j) const { return i * W + j; }

    string shortestPath(int si, int sj, int ti, int tj) {
        const double INF = 1e100;
        vector<double> dist(N, INF);
        vector<int> parent(N, -1);
        vector<char> pch(N, 0);
        priority_queue<pair<double,int>, vector<pair<double,int>>, greater<pair<double,int>>> pq;

        int s = id(si, sj), t = id(ti, tj);
        dist[s] = 0.0;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            if (u == t) break;
            int i = u / W, j = u % W;

            // Up
            if (i > 0) {
                int v = id(i - 1, j);
                double nd = d + colW[j];
                if (nd + 1e-12 < dist[v]) {
                    dist[v] = nd;
                    parent[v] = u;
                    pch[v] = 'U';
                    pq.emplace(nd, v);
                }
            }
            // Down
            if (i + 1 < H) {
                int v = id(i + 1, j);
                double nd = d + colW[j];
                if (nd + 1e-12 < dist[v]) {
                    dist[v] = nd;
                    parent[v] = u;
                    pch[v] = 'D';
                    pq.emplace(nd, v);
                }
            }
            // Left
            if (j > 0) {
                int v = id(i, j - 1);
                double nd = d + rowW[i];
                if (nd + 1e-12 < dist[v]) {
                    dist[v] = nd;
                    parent[v] = u;
                    pch[v] = 'L';
                    pq.emplace(nd, v);
                }
            }
            // Right
            if (j + 1 < W) {
                int v = id(i, j + 1);
                double nd = d + rowW[i];
                if (nd + 1e-12 < dist[v]) {
                    dist[v] = nd;
                    parent[v] = u;
                    pch[v] = 'R';
                    pq.emplace(nd, v);
                }
            }
        }

        if (parent[t] == -1) {
            // Fallback to simple Manhattan path (should not happen)
            string path;
            int ci = si, cj = sj;
            char vdir = (ti < si) ? 'U' : 'D';
            char hdir = (tj < sj) ? 'L' : 'R';
            for (int k = 0; k < abs(ti - si); ++k) path.push_back(vdir);
            for (int k = 0; k < abs(tj - sj); ++k) path.push_back(hdir);
            return path;
        }

        string path;
        int cur = t;
        while (cur != s) {
            path.push_back(pch[cur]);
            cur = parent[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    void updateModel(const string& path, int si, int sj, long long y_observed, int iter) {
        vector<int> xH(H, 0), xV(W, 0);
        int i = si, j = sj;
        for (char c : path) {
            if (c == 'U') { xV[j]++; i--; }
            else if (c == 'D') { xV[j]++; i++; }
            else if (c == 'L') { xH[i]++; j--; }
            else if (c == 'R') { xH[i]++; j++; }
        }

        double y_pred = 0.0;
        for (int r = 0; r < H; ++r) y_pred += rowW[r] * xH[r];
        for (int c = 0; c < W; ++c) y_pred += colW[c] * xV[c];

        if (y_pred <= 0.0) return;

        double y = (double)y_observed;
        int L = (int)path.size();
        if (L <= 0) return;

        double norm = 1.0 / L;
        double ratio = y / y_pred;

        double alpha, eta;
        if (iter < 50) { alpha = 0.40; eta = 0.0010; }
        else if (iter < 200) { alpha = 0.20; eta = 0.0006; }
        else if (iter < 500) { alpha = 0.10; eta = 0.0003; }
        else { alpha = 0.05; eta = 0.0002; }

        // Multiplicative scaling based on ratio
        for (int r = 0; r < H; ++r) {
            if (xH[r] > 0) {
                double f = 1.0 + alpha * (ratio - 1.0) * (xH[r] * norm);
                rowW[r] *= f;
            }
        }
        for (int c = 0; c < W; ++c) {
            if (xV[c] > 0) {
                double f = 1.0 + alpha * (ratio - 1.0) * (xV[c] * norm);
                colW[c] *= f;
            }
        }

        // Additive correction for relative differences
        double e_abs = y_pred - y;
        for (int r = 0; r < H; ++r) {
            if (xH[r] > 0) rowW[r] -= eta * e_abs * (xH[r] * norm);
        }
        for (int c = 0; c < W; ++c) {
            if (xV[c] > 0) colW[c] -= eta * e_abs * (xV[c] * norm);
        }

        // Clamp to plausible range
        for (int r = 0; r < H; ++r) {
            if (rowW[r] < 1000.0) rowW[r] = 1000.0;
            if (rowW[r] > 9000.0) rowW[r] = 9000.0;
        }
        for (int c = 0; c < W; ++c) {
            if (colW[c] < 1000.0) colW[c] = 1000.0;
            if (colW[c] > 9000.0) colW[c] = 9000.0;
        }
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        for (int k = 0; k < 1000; k++) {
            int si, sj, ti, tj;
            if (!(cin >> si >> sj >> ti >> tj)) return;

            string path = shortestPath(si, sj, ti, tj);
            cout << path << endl;
            cout.flush();

            long long feedback;
            if (!(cin >> feedback)) return;

            updateModel(path, si, sj, feedback, k);
        }
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}