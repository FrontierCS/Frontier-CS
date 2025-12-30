#include <bits/stdc++.h>
using namespace std;

struct EdgeRef {
    bool isH; // true: horizontal (i,j)-(i,j+1), false: vertical (i,j)-(i+1,j)
    int i, j;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    const int Q = 1000;
    const double INIT_W = 6000.0;
    const double MIN_W = 100.0;
    const double MAX_W = 20000.0;

    static double wh[30][29]; // horizontal weights
    static double wv[29][30]; // vertical weights
    static int ch[30][29];    // usage counts for wh
    static int cv[29][30];    // usage counts for wv

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N - 1; j++) {
            wh[i][j] = INIT_W;
            ch[i][j] = 0;
        }
    }
    for (int i = 0; i < N - 1; i++) {
        for (int j = 0; j < N; j++) {
            wv[i][j] = INIT_W;
            cv[i][j] = 0;
        }
    }

    auto inb = [&](int i, int j) { return (0 <= i && i < N && 0 <= j && j < N); };

    for (int q = 0; q < Q; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) {
            return 0;
        }

        // Dijkstra on 30x30 grid
        const int V = N * N;
        vector<double> dist(V, 1e100);
        vector<int> prev(V, -1);
        vector<char> moveDir(V, '?');

        auto id = [&](int i, int j) { return i * N + j; };
        int sId = id(si, sj);
        int tId = id(ti, tj);

        using PDI = pair<double, int>;
        priority_queue<PDI, vector<PDI>, greater<PDI>> pq;
        dist[sId] = 0.0;
        pq.emplace(0.0, sId);

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d > dist[u]) continue;
            if (u == tId) break;
            int ui = u / N, uj = u % N;

            // Up
            if (ui - 1 >= 0) {
                double w = wv[ui - 1][uj];
                int v = id(ui - 1, uj);
                double nd = d + w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    moveDir[v] = 'U';
                    pq.emplace(nd, v);
                }
            }
            // Down
            if (ui + 1 < N) {
                double w = wv[ui][uj];
                int v = id(ui + 1, uj);
                double nd = d + w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    moveDir[v] = 'D';
                    pq.emplace(nd, v);
                }
            }
            // Left
            if (uj - 1 >= 0) {
                double w = wh[ui][uj - 1];
                int v = id(ui, uj - 1);
                double nd = d + w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    moveDir[v] = 'L';
                    pq.emplace(nd, v);
                }
            }
            // Right
            if (uj + 1 < N) {
                double w = wh[ui][uj];
                int v = id(ui, uj + 1);
                double nd = d + w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    moveDir[v] = 'R';
                    pq.emplace(nd, v);
                }
            }
        }

        // Reconstruct path
        string path;
        vector<EdgeRef> edges; // edges in order from s to t
        int cur = tId;
        if (cur == sId) {
            // unlikely due to problem constraints, but handle just in case
            cout << "\n" << flush;
            int feedback;
            if (!(cin >> feedback)) return 0;
            continue;
        }
        vector<char> tmpMoves;
        vector<EdgeRef> tmpEdges;
        while (cur != sId && cur != -1) {
            int p = prev[cur];
            char md = moveDir[cur];
            tmpMoves.push_back(md);
            int pi = p / N, pj = p % N;
            int ci = cur / N, cj = cur % N;
            if (md == 'U') {
                // from (pi,pj) to (ci=pi-1,pj)
                tmpEdges.push_back({false, ci, cj}); // v[ci][cj] since ci = pi-1
            } else if (md == 'D') {
                // from (pi,pj) to (ci=pi+1,pj)
                tmpEdges.push_back({false, pi, pj}); // v[pi][pj]
            } else if (md == 'L') {
                // from (pi,pj) to (pi,pj-1)
                tmpEdges.push_back({true, pi, cj}); // h[pi][cj] where cj = pj-1
            } else if (md == 'R') {
                // from (pi,pj) to (pi,pj+1)
                tmpEdges.push_back({true, pi, pj}); // h[pi][pj]
            }
            cur = p;
        }
        reverse(tmpMoves.begin(), tmpMoves.end());
        reverse(tmpEdges.begin(), tmpEdges.end());
        path.assign(tmpMoves.begin(), tmpMoves.end());
        edges = move(tmpEdges);

        cout << path << "\n" << flush;

        int feedback;
        if (!(cin >> feedback)) return 0;

        // Update weights based on observed feedback
        int m = (int)edges.size();
        if (m > 0) {
            double predicted = 0.0;
            for (auto &e : edges) {
                if (e.isH) predicted += wh[e.i][e.j];
                else predicted += wv[e.i][e.j];
            }
            double y = (double)feedback;
            // Additive update distributed along edges on the path with per-edge diminishing step
            double diff = y - predicted;
            // Base learning rate
            double baseEta = 0.3;
            // Adjust eta slightly by path length to keep per-edge update moderated
            double etaPerEdge = baseEta;

            // Distribute update
            for (auto &e : edges) {
                if (e.isH) {
                    int &cnt = ch[e.i][e.j];
                    double step = etaPerEdge / (1.0 + 0.1 * cnt);
                    double delta = step * (diff / m);
                    wh[e.i][e.j] += delta;
                    if (wh[e.i][e.j] < MIN_W) wh[e.i][e.j] = MIN_W;
                    if (wh[e.i][e.j] > MAX_W) wh[e.i][e.j] = MAX_W;
                    cnt++;
                } else {
                    int &cnt = cv[e.i][e.j];
                    double step = etaPerEdge / (1.0 + 0.1 * cnt);
                    double delta = step * (diff / m);
                    wv[e.i][e.j] += delta;
                    if (wv[e.i][e.j] < MIN_W) wv[e.i][e.j] = MIN_W;
                    if (wv[e.i][e.j] > MAX_W) wv[e.i][e.j] = MAX_W;
                    cnt++;
                }
            }
        }
    }
    return 0;
}