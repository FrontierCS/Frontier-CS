#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Solver {
    static constexpr int N = 30;
    static constexpr int Vn = N * N;
    static constexpr int Hn = N * (N - 1);      // 30*29 = 870
    static constexpr int VEn = (N - 1) * N;     // 29*30 = 870
    static constexpr int En = Hn + VEn;         // 1740

    double h[N][N - 1];
    double v[N - 1][N];
    int cnt[En];

    Solver() {
        for (int i = 0; i < N; i++) for (int j = 0; j < N - 1; j++) h[i][j] = 5000.0;
        for (int i = 0; i < N - 1; i++) for (int j = 0; j < N; j++) v[i][j] = 5000.0;
        memset(cnt, 0, sizeof(cnt));
    }

    static inline int vid(int i, int j) { return i * N + j; }

    static inline bool inside(int i, int j) { return 0 <= i && i < N && 0 <= j && j < N; }

    static inline int eid_h(int i, int j) { // between (i,j) and (i,j+1)
        return i * (N - 1) + j;
    }
    static inline int eid_v(int i, int j) { // between (i,j) and (i+1,j)
        return Hn + i * N + j;
    }

    inline int edge_id_between(int i, int j, int ni, int nj) const {
        if (ni == i) {
            if (nj == j + 1) return eid_h(i, j);
            if (nj == j - 1) return eid_h(i, j - 1);
        } else if (nj == j) {
            if (ni == i + 1) return eid_v(i, j);
            if (ni == i - 1) return eid_v(i - 1, j);
        }
        return -1;
    }

    inline double base_weight(int eid) const {
        if (eid < Hn) {
            int i = eid / (N - 1);
            int j = eid % (N - 1);
            return h[i][j];
        } else {
            int id = eid - Hn;
            int i = id / N;
            int j = id % N;
            return v[i][j];
        }
    }

    inline void set_weight(int eid, double w) {
        w = max(100.0, min(10000.0, w));
        if (eid < Hn) {
            int i = eid / (N - 1);
            int j = eid % (N - 1);
            h[i][j] = w;
        } else {
            int id = eid - Hn;
            int i = id / N;
            int j = id % N;
            v[i][j] = w;
        }
    }

    inline double noisy_weight(int eid, int k, double A) const {
        double w = base_weight(eid);
        if (A <= 0) return w;
        uint64_t x = (uint64_t(eid) * 0x9e3779b97f4a7c15ULL) ^ (uint64_t(k) * 0xbf58476d1ce4e5b9ULL);
        uint64_t z = splitmix64(x);
        double u = (z >> 11) * (1.0 / 9007199254740992.0); // [0,1)
        double eps = (u * 2.0 - 1.0) * A;
        double ww = w * (1.0 + eps);
        if (ww < 1.0) ww = 1.0;
        return ww;
    }

    pair<string, vector<int>> dijkstra_path(int si, int sj, int ti, int tj, int k) {
        int s = vid(si, sj);
        int t = vid(ti, tj);

        double A = 0.0;
        if (k < 250) A = 0.20 * (1.0 - double(k) / 250.0);
        else if (k < 600) A = 0.02;

        const long double INF = 1e100L;
        static long double dist[Vn];
        static int parent[Vn];
        static char pmove[Vn];

        for (int i = 0; i < Vn; i++) {
            dist[i] = INF;
            parent[i] = -1;
            pmove[i] = 0;
        }

        using P = pair<long double, int>;
        priority_queue<P, vector<P>, greater<P>> pq;
        dist[s] = 0;
        pq.push({0, s});

        static const int di[4] = {-1, 1, 0, 0};
        static const int dj[4] = {0, 0, -1, 1};
        static const char dc[4] = {'U', 'D', 'L', 'R'};

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d != dist[u]) continue;
            if (u == t) break;
            int i = u / N, j = u % N;

            for (int dir = 0; dir < 4; dir++) {
                int ni = i + di[dir], nj = j + dj[dir];
                if (!inside(ni, nj)) continue;
                int vtx = vid(ni, nj);
                int eid = edge_id_between(i, j, ni, nj);
                double w = noisy_weight(eid, k, A);
                long double nd = d + (long double)w;
                if (nd < dist[vtx]) {
                    dist[vtx] = nd;
                    parent[vtx] = u;
                    pmove[vtx] = dc[dir];
                    pq.push({nd, vtx});
                }
            }
        }

        string path;
        vector<int> eids;

        int cur = t;
        if (cur == s) return {path, eids};

        while (cur != s) {
            int p = parent[cur];
            if (p < 0) { // fallback (should not happen)
                path.clear();
                eids.clear();
                int ci = si, cj = sj;
                while (ci < ti) { path.push_back('D'); eids.push_back(edge_id_between(ci, cj, ci + 1, cj)); ci++; }
                while (ci > ti) { path.push_back('U'); eids.push_back(edge_id_between(ci, cj, ci - 1, cj)); ci--; }
                while (cj < tj) { path.push_back('R'); eids.push_back(edge_id_between(ci, cj, ci, cj + 1)); cj++; }
                while (cj > tj) { path.push_back('L'); eids.push_back(edge_id_between(ci, cj, ci, cj - 1)); cj--; }
                return {path, eids};
            }
            int pi = p / N, pj = p % N;
            int ci = cur / N, cj = cur % N;
            char mv = pmove[cur];
            path.push_back(mv);
            eids.push_back(edge_id_between(pi, pj, ci, cj));
            cur = p;
        }

        reverse(path.begin(), path.end());
        reverse(eids.begin(), eids.end());
        return {path, eids};
    }

    void update(const vector<int>& eids, long long observed, int k) {
        if (eids.empty()) return;
        double y = (double)observed;

        double yhat = 0.0;
        for (int eid : eids) yhat += base_weight(eid);

        double residual = y - yhat;
        int m = (int)eids.size();

        // Learning rate schedule: small due to noise (0.9..1.1).
        double base_lr = 0.12;
        if (k < 30) base_lr = 0.18;
        else if (k < 150) base_lr = 0.14;
        else if (k < 400) base_lr = 0.11;
        else base_lr = 0.09;

        // Cap residual impact (robustness against occasional bad exploration + noise).
        double per_edge_raw = residual / (double)m;
        per_edge_raw = max(-6000.0, min(6000.0, per_edge_raw));

        for (int eid : eids) {
            cnt[eid]++;
            double lr = base_lr / sqrt((double)cnt[eid]);
            double delta = lr * per_edge_raw;
            delta = max(-180.0, min(180.0, delta));
            set_weight(eid, base_weight(eid) + delta);
        }
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        for (int k = 0; k < 1000; k++) {
            int si, sj, ti, tj;
            if (!(cin >> si >> sj >> ti >> tj)) break;

            auto [path, eids] = dijkstra_path(si, sj, ti, tj, k);

            cout << path << "\n" << flush;

            long long r;
            if (!(cin >> r)) break;

            update(eids, r, k);
        }
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}