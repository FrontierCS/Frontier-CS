#include <bits/stdc++.h>
using namespace std;

struct EdgeUse {
    bool horiz; // true if horizontal, false if vertical
    int i, j;   // indices: for horiz -> h[i][j], for vert -> v[i][j]
};

static const int N = 30;
static const int HN = N, HM = N - 1; // h[i][j], i in [0,29], j in [0,28]
static const int VN = N - 1, VM = N; // v[i][j], i in [0,28], j in [0,29]
static const double MINW = 1000.0;
static const double MAXW = 9000.0;

int nodeId(int i, int j) { return i * N + j; }
pair<int,int> nodePos(int id) { return {id / N, id % N}; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Model parameters
    // Base per-row for horizontal edges and per-column for vertical edges
    array<double, N> baseH; // row biases for horizontal edges
    array<double, N> baseV; // col biases for vertical edges
    // Residuals per edge
    static double resH[HN][HM];
    static double resV[VN][VM];

    // Initialize
    for (int i = 0; i < N; i++) {
        baseH[i] = 6000.0;
        baseV[i] = 6000.0;
    }
    for (int i = 0; i < HN; i++) for (int j = 0; j < HM; j++) resH[i][j] = 0.0;
    for (int i = 0; i < VN; i++) for (int j = 0; j < VM; j++) resV[i][j] = 0.0;

    auto clampW = [&](double w)->double {
        if (w < MINW) return MINW;
        if (w > MAXW) return MAXW;
        return w;
    };

    // Precomputed weights for current query
    static double wH[HN][HM];
    static double wV[VN][VM];

    auto rebuildWeights = [&]() {
        for (int i = 0; i < HN; i++) {
            for (int j = 0; j < HM; j++) {
                wH[i][j] = clampW(baseH[i] + resH[i][j]);
            }
        }
        for (int i = 0; i < VN; i++) {
            for (int j = 0; j < VM; j++) {
                wV[i][j] = clampW(baseV[j] + resV[i][j]);
            }
        }
    };

    // Dijkstra to find path from s to t using current weights
    auto shortestPath = [&](int si, int sj, int ti, int tj, string &path, vector<EdgeUse> &edges) {
        const int V = N * N;
        const double INF = 1e100;
        static double dist[V];
        static int prevId[V];
        static char prevDir[V];
        static bool used[V];

        for (int i = 0; i < V; i++) {
            dist[i] = INF;
            prevId[i] = -1;
            prevDir[i] = 0;
            used[i] = false;
        }

        int s = nodeId(si, sj);
        int t = nodeId(ti, tj);
        dist[s] = 0.0;

        using P = pair<double, int>;
        priority_queue<P, vector<P>, greater<P>> pq;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (used[u]) continue;
            used[u] = true;
            if (u == t) break;
            auto [ui, uj] = nodePos(u);

            // up
            if (ui > 0) {
                int vi = ui - 1, vj = uj;
                int v = nodeId(vi, vj);
                double w = wV[ui - 1][uj];
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prevId[v] = u;
                    prevDir[v] = 'U'; // from u to v (moving up)
                    pq.emplace(dist[v], v);
                }
            }
            // down
            if (ui < N - 1) {
                int vi = ui + 1, vj = uj;
                int v = nodeId(vi, vj);
                double w = wV[ui][uj];
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prevId[v] = u;
                    prevDir[v] = 'D'; // moving down
                    pq.emplace(dist[v], v);
                }
            }
            // left
            if (uj > 0) {
                int vi = ui, vj = uj - 1;
                int v = nodeId(vi, vj);
                double w = wH[ui][uj - 1];
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prevId[v] = u;
                    prevDir[v] = 'L'; // moving left
                    pq.emplace(dist[v], v);
                }
            }
            // right
            if (uj < N - 1) {
                int vi = ui, vj = uj + 1;
                int v = nodeId(vi, vj);
                double w = wH[ui][uj];
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prevId[v] = u;
                    prevDir[v] = 'R'; // moving right
                    pq.emplace(dist[v], v);
                }
            }
        }

        // reconstruct
        path.clear();
        edges.clear();
        int cur = t;
        if (prevId[cur] == -1 && cur != s) {
            // fallback to simple Manhattan path if unreachable (should not happen)
            int ci = si, cj = sj;
            while (ci < ti) { path.push_back('D'); ci++; }
            while (ci > ti) { path.push_back('U'); ci--; }
            while (cj < tj) { path.push_back('R'); cj++; }
            while (cj > tj) { path.push_back('L'); cj--; }
        } else {
            string rev;
            while (cur != s) {
                char c = prevDir[cur];
                rev.push_back(c);
                cur = prevId[cur];
            }
            reverse(rev.begin(), rev.end());
            path = rev;
        }

        // Build edges along the path
        int ci = si, cj = sj;
        for (char c : path) {
            if (c == 'U') {
                // (ci, cj) -> (ci-1, cj) uses v[ci-1][cj]
                edges.push_back({false, ci - 1, cj});
                ci -= 1;
            } else if (c == 'D') {
                // uses v[ci][cj]
                edges.push_back({false, ci, cj});
                ci += 1;
            } else if (c == 'L') {
                // uses h[ci][cj-1]
                edges.push_back({true, ci, cj - 1});
                cj -= 1;
            } else if (c == 'R') {
                // uses h[ci][cj]
                edges.push_back({true, ci, cj});
                cj += 1;
            }
        }
    };

    // Reading loop for queries
    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) {
            return 0;
        }

        // Rebuild weight arrays for this query
        rebuildWeights();

        // Plan path
        string path;
        vector<EdgeUse> edges;
        shortestPath(si, sj, ti, tj, path, edges);

        // Output path and flush
        cout << path << endl;
        cout.flush();

        // Read feedback (observed length with noise)
        int observedInt;
        if (!(cin >> observedInt)) {
            return 0;
        }
        double observed = (double)observedInt;

        // Predicted length using current weights
        double predicted = 0.0;
        int L = (int)edges.size();
        int Lh = 0, Lv = 0;
        static int rowCountH[HN];
        static int colCountV[VM];
        for (int i = 0; i < HN; i++) rowCountH[i] = 0;
        for (int j = 0; j < VM; j++) colCountV[j] = 0;

        for (auto &e : edges) {
            if (e.horiz) {
                predicted += wH[e.i][e.j];
                Lh++;
                rowCountH[e.i]++;
            } else {
                predicted += wV[e.i][e.j];
                Lv++;
                colCountV[e.j]++;
            }
        }

        if (L == 0) continue; // s == t (shouldn't happen due to distance >= 10)

        double err = observed - predicted;

        // Learning rates and portions with schedule
        double basePortion = 0.7;
        double lrBase, lrRes;
        if (q < 200) {
            lrBase = 0.35;
            lrRes  = 0.25;
        } else if (q < 600) {
            lrBase = 0.20;
            lrRes  = 0.18;
        } else {
            lrBase = 0.12;
            lrRes  = 0.12;
        }

        double errBase = basePortion * err;
        double errRes  = (1.0 - basePortion) * err;

        // Update base biases
        if (Lh > 0) {
            double totalH = 0.0;
            for (int i = 0; i < HN; i++) totalH += rowCountH[i];
            if (totalH > 0.0) {
                double shareH = errBase * (double)Lh / (double)L; // portion allocated to horizontal
                for (int i = 0; i < HN; i++) {
                    if (rowCountH[i] > 0) {
                        baseH[i] += lrBase * shareH * ((double)rowCountH[i] / (double)Lh);
                        if (baseH[i] < MINW) baseH[i] = MINW;
                        if (baseH[i] > MAXW) baseH[i] = MAXW;
                    }
                }
            }
        }
        if (Lv > 0) {
            double totalV = 0.0;
            for (int j = 0; j < VM; j++) totalV += colCountV[j];
            if (totalV > 0.0) {
                double shareV = errBase * (double)Lv / (double)L; // portion allocated to vertical
                for (int j = 0; j < VM; j++) {
                    if (colCountV[j] > 0) {
                        baseV[j] += lrBase * shareV * ((double)colCountV[j] / (double)Lv);
                        if (baseV[j] < MINW) baseV[j] = MINW;
                        if (baseV[j] > MAXW) baseV[j] = MAXW;
                    }
                }
            }
        }

        // Update residuals per edge
        double perEdgeUpdate = lrRes * errRes / (double)L;
        if (perEdgeUpdate != 0.0) {
            for (auto &e : edges) {
                if (e.horiz) {
                    resH[e.i][e.j] += perEdgeUpdate;
                    // Keep overall within reasonable bounds by soft clamp on residuals
                    double curW = baseH[e.i] + resH[e.i][e.j];
                    if (curW < MINW) resH[e.i][e.j] = MINW - baseH[e.i];
                    if (curW > MAXW) resH[e.i][e.j] = MAXW - baseH[e.i];
                } else {
                    resV[e.i][e.j] += perEdgeUpdate;
                    double curW = baseV[e.j] + resV[e.i][e.j];
                    if (curW < MINW) resV[e.i][e.j] = MINW - baseV[e.j];
                    if (curW > MAXW) resV[e.i][e.j] = MAXW - baseV[e.j];
                }
            }
        }
    }

    return 0;
}