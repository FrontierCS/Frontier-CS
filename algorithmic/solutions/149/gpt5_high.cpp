#include <bits/stdc++.h>
using namespace std;

struct RLS {
    int F;
    double lambda;
    vector<double> w;
    vector<vector<double>> P;

    RLS(int F_, double lambda_, double init_w = 5000.0) : F(F_), lambda(lambda_) {
        w.assign(F, init_w);
        P.assign(F, vector<double>(F, 0.0));
        double inv_lambda = 1.0 / lambda;
        for (int i = 0; i < F; i++) P[i][i] = inv_lambda;
    }

    void update(const vector<double>& x, double y) {
        // g = P x / (1 + x^T P x)
        vector<double> Px(F, 0.0);
        for (int i = 0; i < F; i++) {
            double s = 0.0;
            const vector<double>& Pi = P[i];
            for (int j = 0; j < F; j++) s += Pi[j] * x[j];
            Px[i] = s;
        }
        double denom = 1.0;
        for (int i = 0; i < F; i++) denom += x[i] * Px[i];
        if (denom <= 0) denom = 1e-9;
        vector<double> g(F, 0.0);
        for (int i = 0; i < F; i++) g[i] = Px[i] / denom;

        // residual r = y - x^T w
        double yhat = 0.0;
        for (int i = 0; i < F; i++) yhat += x[i] * w[i];
        double r = y - yhat;

        // w = w + g * r
        for (int i = 0; i < F; i++) w[i] += g[i] * r;

        // P = P - (P x x^T P) / denom = P - outer(Px, Px)/denom
        for (int i = 0; i < F; i++) {
            for (int j = 0; j < F; j++) {
                P[i][j] -= (Px[i] * Px[j]) / denom;
            }
        }
    }
};

struct Solver {
    static constexpr int N = 30;
    static constexpr int B = 3; // segments per axis
    static constexpr int F = N * B * 2; // H + V features
    RLS rls;
    Solver() : rls(F, 1.0, 5000.0) {}

    inline int segH(int j) const {
        if (j < 10) return 0;
        if (j < 20) return 1;
        return 2;
    }
    inline int segV(int i) const {
        if (i < 10) return 0;
        if (i < 20) return 1;
        return 2;
    }
    inline int idxH(int i, int s) const { // 0..N*B-1
        return i * B + s;
    }
    inline int idxV(int j, int s) const { // N*B..N*B + N*B-1
        return N * B + j * B + s;
    }

    inline double hor_cost(int i, int j) const {
        int s = segH(j);
        double val = rls.w[idxH(i, s)];
        if (val < 1.0) val = 1.0;
        return val;
    }
    inline double ver_cost(int i, int j) const {
        int s = segV(i);
        double val = rls.w[idxV(j, s)];
        if (val < 1.0) val = 1.0;
        return val;
    }

    string dijkstra(int si, int sj, int ti, int tj) {
        const int V = N * N;
        auto id = [&](int i, int j) { return i * N + j; };
        auto ij = [&](int idv) { return pair<int,int>(idv / N, idv % N); };

        vector<double> dist(V, 1e100);
        vector<int> prev(V, -1);
        vector<char> prevMove(V, '?');

        int s = id(si, sj);
        int t = id(ti, tj);
        dist[s] = 0.0;

        using PDI = pair<double,int>;
        priority_queue<PDI, vector<PDI>, greater<PDI>> pq;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d != dist[u]) continue;
            if (u == t) break;
            auto [i, j] = ij(u);

            // Left
            if (j > 0) {
                int v = id(i, j - 1);
                double w = hor_cost(i, j - 1);
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prev[v] = u;
                    prevMove[v] = 'L';
                    pq.emplace(dist[v], v);
                }
            }
            // Right
            if (j < N - 1) {
                int v = id(i, j + 1);
                double w = hor_cost(i, j);
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prev[v] = u;
                    prevMove[v] = 'R';
                    pq.emplace(dist[v], v);
                }
            }
            // Up
            if (i > 0) {
                int v = id(i - 1, j);
                double w = ver_cost(i - 1, j);
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prev[v] = u;
                    prevMove[v] = 'U';
                    pq.emplace(dist[v], v);
                }
            }
            // Down
            if (i < N - 1) {
                int v = id(i + 1, j);
                double w = ver_cost(i, j);
                if (dist[v] > d + w) {
                    dist[v] = d + w;
                    prev[v] = u;
                    prevMove[v] = 'D';
                    pq.emplace(dist[v], v);
                }
            }
        }

        string path;
        if (prev[t] == -1 && s != t) {
            // Fallback to simple Manhattan path if Dijkstra failed (shouldn't happen)
            int i = si, j = sj;
            while (i < ti) { path.push_back('D'); i++; }
            while (i > ti) { path.push_back('U'); i--; }
            while (j < tj) { path.push_back('R'); j++; }
            while (j > tj) { path.push_back('L'); j--; }
            return path;
        }

        int cur = t;
        while (cur != s) {
            path.push_back(prevMove[cur]);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    vector<double> path_features(int si, int sj, const string& path) const {
        vector<double> x(F, 0.0);
        int i = si, j = sj;
        for (char c : path) {
            if (c == 'L') {
                int jj = j - 1;
                if (jj >= 0) {
                    x[idxH(i, segH(jj))] += 1.0;
                }
                j = jj;
            } else if (c == 'R') {
                int jj = j;
                x[idxH(i, segH(jj))] += 1.0;
                j = j + 1;
            } else if (c == 'U') {
                int ii = i - 1;
                if (ii >= 0) {
                    x[idxV(j, segV(ii))] += 1.0;
                }
                i = ii;
            } else if (c == 'D') {
                int ii = i;
                x[idxV(j, segV(ii))] += 1.0;
                i = i + 1;
            }
        }
        return x;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;

    for (int q = 0; q < 1000; q++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) {
            return 0;
        }
        string path = solver.dijkstra(si, sj, ti, tj);

        cout << path << '\n' << flush;

        long long observed;
        if (!(cin >> observed)) {
            return 0;
        }

        vector<double> x = solver.path_features(si, sj, path);
        solver.rls.update(x, (double)observed);
    }

    return 0;
}