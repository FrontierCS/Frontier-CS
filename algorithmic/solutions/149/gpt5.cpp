#include <bits/stdc++.h>
using namespace std;

struct Solver {
    static const int H = 30, W = 30, DIMS = 60;
    vector<double> r, c;
    double AtA[DIMS][DIMS];
    double Atb[DIMS];
    double lambda;
    double mu;

    Solver() {
        r.assign(H, 6000.0);
        c.assign(W, 6000.0);
        memset(AtA, 0, sizeof(AtA));
        memset(Atb, 0, sizeof(Atb));
        lambda = 1.0;
        mu = 6000.0;
    }

    inline int id(int i, int j) const { return i * W + j; }

    string dijkstra_path(int si, int sj, int ti, int tj) {
        const int n = H * W;
        const double INF = 1e100;
        vector<double> dist(n, INF);
        vector<int> prev(n, -1);
        vector<char> pmove(n, '?');
        int s = id(si, sj), t = id(ti, tj);
        priority_queue<pair<double,int>, vector<pair<double,int>>, greater<pair<double,int>>> pq;
        dist[s] = 0.0;
        pq.push({0.0, s});

        auto try_push = [&](int ui, int uj, int vi, int vj, char m, double w) {
            int u = id(ui, uj);
            int v = id(vi, vj);
            double nd = dist[u] + w;
            if (nd < dist[v]) {
                dist[v] = nd;
                prev[v] = u;
                pmove[v] = m;
                pq.push({nd, v});
            }
        };

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d != dist[u]) continue;
            if (u == t) break;
            int i = u / W, j = u % W;
            if (i > 0) try_push(i, j, i - 1, j, 'U', c[j]);
            if (i + 1 < H) try_push(i, j, i + 1, j, 'D', c[j]);
            if (j > 0) try_push(i, j, i, j - 1, 'L', r[i]);
            if (j + 1 < W) try_push(i, j, i, j + 1, 'R', r[i]);
        }

        string path;
        int cur = t;
        if (prev[cur] == -1 && cur != s) {
            // Fallback: simple Manhattan path
            int di = ti - si, dj = tj - sj;
            if (dj > 0) path.append(dj, 'R'); else path.append(-dj, 'L');
            if (di > 0) path.append(di, 'D'); else path.append(-di, 'U');
            return path;
        }
        while (cur != s) {
            char m = pmove[cur];
            path.push_back(m);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    void solve_theta() {
        int n = DIMS;
        vector<vector<double>> M(n, vector<double>(n, 0.0));
        vector<double> rhs(n, 0.0);
        for (int i = 0; i < n; i++) {
            rhs[i] = Atb[i] + lambda * mu;
            for (int j = 0; j < n; j++) {
                M[i][j] = AtA[i][j];
            }
            M[i][i] += lambda;
        }

        vector<vector<double>> L(n, vector<double>(n, 0.0));
        for (int i = 0; i < n; i++) {
            for (int j = 0; j <= i; j++) {
                double sum = M[i][j];
                for (int k = 0; k < j; k++) sum -= L[i][k] * L[j][k];
                if (i == j) {
                    if (sum <= 1e-12) sum = 1e-12;
                    L[i][i] = sqrt(sum);
                } else {
                    if (fabs(L[j][j]) < 1e-15) L[j][j] = 1e-7;
                    L[i][j] = sum / L[j][j];
                }
            }
        }

        vector<double> y(n, 0.0), x(n, 0.0);
        for (int i = 0; i < n; i++) {
            double sum = rhs[i];
            for (int k = 0; k < i; k++) sum -= L[i][k] * y[k];
            y[i] = sum / L[i][i];
        }
        for (int i = n - 1; i >= 0; i--) {
            double sum = y[i];
            for (int k = i + 1; k < n; k++) sum -= L[k][i] * x[k];
            x[i] = sum / L[i][i];
        }

        for (int i = 0; i < 30; i++) {
            double val = x[i];
            if (!(val == val)) val = 6000.0;
            val = max(100.0, min(10000.0, val));
            r[i] = val;
        }
        for (int j = 0; j < 30; j++) {
            double val = x[30 + j];
            if (!(val == val)) val = 6000.0;
            val = max(100.0, min(10000.0, val));
            c[j] = val;
        }
    }

    void update_with_path(int si, int sj, const string& path, int measured) {
        double f[DIMS];
        for (int i = 0; i < DIMS; i++) f[i] = 0.0;
        int i = si, j = sj;
        for (char ch : path) {
            if (ch == 'U') {
                f[30 + j] += 1.0;
                i -= 1;
            } else if (ch == 'D') {
                f[30 + j] += 1.0;
                i += 1;
            } else if (ch == 'L') {
                f[i] += 1.0;
                j -= 1;
            } else if (ch == 'R') {
                f[i] += 1.0;
                j += 1;
            }
        }
        for (int a = 0; a < DIMS; a++) {
            Atb[a] += f[a] * measured;
            for (int b = 0; b < DIMS; b++) {
                AtA[a][b] += f[a] * f[b];
            }
        }
        solve_theta();
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

        string path = solver.dijkstra_path(si, sj, ti, tj);
        cout << path << endl;
        cout.flush();

        int measured;
        if (!(cin >> measured)) {
            return 0;
        }

        solver.update_with_path(si, sj, path, measured);
    }

    return 0;
}