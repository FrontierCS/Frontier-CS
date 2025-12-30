#include <bits/stdc++.h>
using namespace std;

struct Estimator {
    static constexpr int H = 30, W = 30;
    static constexpr double INIT_W = 5000.0;
    static constexpr double MIN_W = 100.0;
    static constexpr double MAX_W = 20000.0;

    // Base weights per row/column
    array<double, H> baseH;
    array<double, W> baseV;

    // Local deviations per edge (horizontal and vertical)
    double devH[H][W-1];
    double devV[H-1][W];

    // Visit counts for adaptive step sizes
    int cntDevH[H][W-1];
    int cntDevV[H-1][W];

    Estimator() {
        for (int i = 0; i < H; ++i) baseH[i] = INIT_W;
        for (int j = 0; j < W; ++j) baseV[j] = INIT_W;
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W-1; ++j) {
                devH[i][j] = 0.0;
                cntDevH[i][j] = 0;
            }
        }
        for (int i = 0; i < H-1; ++i) {
            for (int j = 0; j < W; ++j) {
                devV[i][j] = 0.0;
                cntDevV[i][j] = 0;
            }
        }
    }

    inline double clampW(double x) const {
        if (x < MIN_W) return MIN_W;
        if (x > MAX_W) return MAX_W;
        return x;
    }

    inline double getH(int i, int j) const { // edge between (i,j) and (i,j+1)
        return clampW(baseH[i] + devH[i][j]);
    }

    inline double getV(int i, int j) const { // edge between (i,j) and (i+1,j)
        return clampW(baseV[j] + devV[i][j]);
    }

    // Dijkstra to compute path from s to t
    string shortest_path(pair<int,int> s, pair<int,int> t) {
        int N = H * W;
        vector<double> dist(N, 1e100);
        vector<int> prev(N, -1);
        vector<char> prevDir(N, '?');

        auto id = [&](int r, int c){ return r * W + c; };
        auto inb = [&](int r, int c){ return (0 <= r && r < H && 0 <= c && c < W); };

        using PDI = pair<double,int>;
        priority_queue<PDI, vector<PDI>, greater<PDI>> pq;

        int sid = id(s.first, s.second);
        int tid = id(t.first, t.second);
        dist[sid] = 0.0;
        pq.emplace(0.0, sid);

        static const int dr[4] = {-1, 1, 0, 0};
        static const int dc[4] = {0, 0, -1, 1};
        static const char dch[4] = {'U','D','L','R'};

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d != dist[u]) continue;
            if (u == tid) break;
            int ur = u / W, uc = u % W;
            for (int k = 0; k < 4; ++k) {
                int vr = ur + dr[k], vc = uc + dc[k];
                if (!inb(vr, vc)) continue;
                double w = 0.0;
                if (k == 0) { // U: (ur,uc) -> (ur-1,uc): vertical edge v[ur-1][uc]
                    w = getV(ur-1, uc);
                } else if (k == 1) { // D: v[ur][uc]
                    w = getV(ur, uc);
                } else if (k == 2) { // L: h[ur][uc-1]
                    w = getH(ur, uc-1);
                } else { // R: h[ur][uc]
                    w = getH(ur, uc);
                }
                int v = id(vr, vc);
                double nd = d + w;
                if (nd < dist[v]) {
                    dist[v] = nd;
                    prev[v] = u;
                    prevDir[v] = dch[k];
                    pq.emplace(nd, v);
                }
            }
        }

        // Reconstruct
        string path;
        if (prev[tid] == -1 && sid != tid) {
            // Should not happen, but fallback to simple Manhattan path
            int r = s.first, c = s.second;
            while (r < t.first) { path.push_back('D'); ++r; }
            while (r > t.first) { path.push_back('U'); --r; }
            while (c < t.second) { path.push_back('R'); ++c; }
            while (c > t.second) { path.push_back('L'); --c; }
            return path;
        }
        int cur = tid;
        while (cur != sid) {
            char ch = prevDir[cur];
            path.push_back(ch);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    // Update model based on observed noisy length for taken path
    void update_model(pair<int,int> s, const string& path, long long observed, int turn_k) {
        if (path.empty()) return;

        // Hyperparameters
        // Small multiplicative step for base weights to reduce effect of noise
        double baseAlpha = 0.04;
        // Slightly decay over turns
        baseAlpha *= (0.98 + 0.02 * (1.0 - double(turn_k) / 1000.0)); // mild decay

        // Additive step for local deviations
        double devEta = 0.06;
        devEta *= (0.98 + 0.02 * (1.0 - double(turn_k) / 1000.0));

        // Compute predicted sums and counts
        vector<int> hRowCount(H, 0), vColCount(W, 0);
        double s_base = 0.0, s_dev = 0.0, s_pred = 0.0;

        struct StepRec {
            bool isH;
            int i, j; // indices into dev arrays
        };
        vector<StepRec> steps;
        steps.reserve(path.size());

        int r = s.first, c = s.second;
        for (char ch : path) {
            if (ch == 'U') {
                // v[r-1][c]
                s_base += baseV[c];
                s_dev += devV[r-1][c];
                s_pred += baseV[c] + devV[r-1][c];
                vColCount[c]++;
                steps.push_back({false, r-1, c});
                r -= 1;
            } else if (ch == 'D') {
                // v[r][c]
                s_base += baseV[c];
                s_dev += devV[r][c];
                s_pred += baseV[c] + devV[r][c];
                vColCount[c]++;
                steps.push_back({false, r, c});
                r += 1;
            } else if (ch == 'L') {
                // h[r][c-1]
                s_base += baseH[r];
                s_dev += devH[r][c-1];
                s_pred += baseH[r] + devH[r][c-1];
                hRowCount[r]++;
                steps.push_back({true, r, c-1});
                c -= 1;
            } else if (ch == 'R') {
                // h[r][c]
                s_base += baseH[r];
                s_dev += devH[r][c];
                s_pred += baseH[r] + devH[r][c];
                hRowCount[r]++;
                steps.push_back({true, r, c});
                c += 1;
            }
        }

        if (s_pred <= 0.0) return;

        // Ratio and residual
        double ratio = double(observed) / s_pred;
        // Clamp ratio to reduce outlier effects from noise
        ratio = max(0.7, min(1.3, ratio));
        double delta = double(observed) - s_pred;

        // Update base weights multiplicatively, distributing by each base's contribution share
        if (s_base > 0.0) {
            // Rows (horizontal base)
            for (int i = 0; i < H; ++i) {
                if (hRowCount[i] == 0) continue;
                double share = (baseH[i] * hRowCount[i]) / s_base;
                double mult = 1.0 + baseAlpha * (ratio - 1.0) * share;
                // Clamp multiplier mildly
                mult = max(0.85, min(1.15, mult));
                baseH[i] = clampW(baseH[i] * mult);
            }
            // Columns (vertical base)
            for (int j = 0; j < W; ++j) {
                if (vColCount[j] == 0) continue;
                double share = (baseV[j] * vColCount[j]) / s_base;
                double mult = 1.0 + baseAlpha * (ratio - 1.0) * share;
                mult = max(0.85, min(1.15, mult));
                baseV[j] = clampW(baseV[j] * mult);
            }
        }

        // Update local deviations additively with small step, normalized by path length and visit count
        int L = (int)path.size();
        if (L > 0) {
            for (auto &st : steps) {
                if (st.isH) {
                    int i = st.i, j = st.j;
                    double step = devEta * (delta / L) / sqrt(double(cntDevH[i][j]) + 1.0);
                    devH[i][j] += step;
                    // Regularization towards 0
                    devH[i][j] *= 0.999;
                    // Clamp to reasonable deviation range
                    if (devH[i][j] < -3000.0) devH[i][j] = -3000.0;
                    if (devH[i][j] >  3000.0) devH[i][j] =  3000.0;
                    cntDevH[i][j]++;
                } else {
                    int i = st.i, j = st.j;
                    double step = devEta * (delta / L) / sqrt(double(cntDevV[i][j]) + 1.0);
                    devV[i][j] += step;
                    devV[i][j] *= 0.999;
                    if (devV[i][j] < -3000.0) devV[i][j] = -3000.0;
                    if (devV[i][j] >  3000.0) devV[i][j] =  3000.0;
                    cntDevV[i][j]++;
                }
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Estimator est;

    for (int k = 0; k < 1000; ++k) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) {
            break;
        }

        string path = est.shortest_path({si, sj}, {ti, tj});

        cout << path << '\n';
        cout.flush();

        long long observed;
        if (!(cin >> observed)) {
            break;
        }

        est.update_model({si, sj}, path, observed, k);
    }
    return 0;
}