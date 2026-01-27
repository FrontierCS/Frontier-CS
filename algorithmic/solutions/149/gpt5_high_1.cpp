#include <bits/stdc++.h>
using namespace std;

struct RLS {
    int d;
    vector<double> w;       // parameter vector
    vector<double> P;       // inverse covariance matrix (flattened d x d)
    double lambda;          // ridge coefficient
    double priorMean;       // prior mean for parameters

    void init(int dim, double lam, double prior) {
        d = dim;
        lambda = lam;
        priorMean = prior;
        w.assign(d, priorMean);
        P.assign(d * d, 0.0);
        double invlam = 1.0 / lambda;
        for (int i = 0; i < d; i++) P[i * d + i] = invlam; // P0 = (1/lambda) * I
    }

    // Update with feature counts f (size d), target y (observed length)
    void update(const vector<int>& f, double y) {
        long long L = 0;
        for (int i = 0; i < d; i++) L += f[i];
        if (L <= 0) return;
        double s = 1.0 / (double)L; // scale to reduce heteroscedasticity
        vector<double> fv(d);
        for (int i = 0; i < d; i++) fv[i] = f[i] * s;
        double ysc = y * s;

        // t = P * fv
        vector<double> t(d, 0.0);
        for (int i = 0; i < d; i++) {
            double acc = 0.0;
            const double* Pi = &P[i * d];
            for (int j = 0; j < d; j++) acc += Pi[j] * fv[j];
            t[i] = acc;
        }
        // denom = 1 + fv^T * t
        double denom = 1.0;
        for (int i = 0; i < d; i++) denom += fv[i] * t[i];
        if (denom <= 1e-12) denom = 1e-12;

        // K = t / denom
        vector<double> K(d);
        for (int i = 0; i < d; i++) K[i] = t[i] / denom;

        // err = y' - fv^T * w
        double pred = 0.0;
        for (int i = 0; i < d; i++) pred += fv[i] * w[i];
        double err = ysc - pred;

        // w = w + K * err
        for (int i = 0; i < d; i++) w[i] += K[i] * err;

        // P = P - K * t^T
        for (int i = 0; i < d; i++) {
            double Ki = K[i];
            double* Pi = &P[i * d];
            for (int j = 0; j < d; j++) {
                Pi[j] -= Ki * t[j];
            }
        }
    }
};

struct Solver {
    static const int H = 30;
    static const int W = 30;
    static const int N = H * W;
    RLS rls;
    Solver() {
        int d = 60; // 30 rows for horizontal, 30 cols for vertical
        double lambda = 1.0;
        double prior = 5000.0;
        rls.init(d, lambda, prior);
    }

    inline int id(int i, int j) const { return i * W + j; }

    // Dijkstra to compute path using current estimated weights
    string shortest_path(int si, int sj, int ti, int tj) {
        vector<double> dist(N, 1e100);
        vector<int> prev(N, -1);
        vector<char> prevDir(N, 0);

        auto rowW = [&](int i)->double {
            double v = rls.w[i];
            if (v < 1.0) v = 1.0;
            return v;
        };
        auto colW = [&](int j)->double {
            double v = rls.w[30 + j];
            if (v < 1.0) v = 1.0;
            return v;
        };

        int s = id(si, sj);
        int t = id(ti, tj);
        dist[s] = 0.0;
        using PDI = pair<double,int>;
        priority_queue<PDI, vector<PDI>, greater<PDI>> pq;
        pq.emplace(0.0, s);

        while (!pq.empty()) {
            auto [dcur, vtx] = pq.top();
            pq.pop();
            if (dcur != dist[vtx]) continue;
            if (vtx == t) break;
            int i = vtx / W, j = vtx % W;

            // neighbors: U, D, L, R
            if (i > 0) {
                int to = id(i - 1, j);
                double w = colW(j);
                if (dist[to] > dcur + w) {
                    dist[to] = dcur + w;
                    prev[to] = vtx;
                    prevDir[to] = 'U';
                    pq.emplace(dist[to], to);
                }
            }
            if (i + 1 < H) {
                int to = id(i + 1, j);
                double w = colW(j);
                if (dist[to] > dcur + w) {
                    dist[to] = dcur + w;
                    prev[to] = vtx;
                    prevDir[to] = 'D';
                    pq.emplace(dist[to], to);
                }
            }
            if (j > 0) {
                int to = id(i, j - 1);
                double w = rowW(i);
                if (dist[to] > dcur + w) {
                    dist[to] = dcur + w;
                    prev[to] = vtx;
                    prevDir[to] = 'L';
                    pq.emplace(dist[to], to);
                }
            }
            if (j + 1 < W) {
                int to = id(i, j + 1);
                double w = rowW(i);
                if (dist[to] > dcur + w) {
                    dist[to] = dcur + w;
                    prev[to] = vtx;
                    prevDir[to] = 'R';
                    pq.emplace(dist[to], to);
                }
            }
        }

        // reconstruct path
        string path;
        int cur = t;
        if (prev[cur] == -1 && cur != s) {
            // fallback: simple Manhattan path if somehow unreachable (shouldn't happen)
            path.clear();
            int i = si, j = sj;
            while (i < ti) { path.push_back('D'); i++; }
            while (i > ti) { path.push_back('U'); i--; }
            while (j < tj) { path.push_back('R'); j++; }
            while (j > tj) { path.push_back('L'); j--; }
            return path;
        }
        while (cur != s) {
            char c = prevDir[cur];
            path.push_back(c);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        for (int q = 0; q < 1000; q++) {
            int si, sj, ti, tj;
            if (!(cin >> si >> sj >> ti >> tj)) return;

            string path = shortest_path(si, sj, ti, tj);

            cout << path << "\n" << flush;

            long long feedback;
            if (!(cin >> feedback)) return;

            // Build feature vector counts from the path
            vector<int> f(60, 0);
            int i = si, j = sj;
            for (char c : path) {
                if (c == 'U') {
                    // move to (i-1, j): vertical edge at column j
                    f[30 + j]++;
                    i -= 1;
                } else if (c == 'D') {
                    f[30 + j]++;
                    i += 1;
                } else if (c == 'L') {
                    f[i]++;
                    j -= 1;
                } else if (c == 'R') {
                    f[i]++;
                    j += 1;
                }
            }
            rls.update(f, (double)feedback);
        }
    }
};

int main() {
    Solver solver;
    solver.run();
    return 0;
}