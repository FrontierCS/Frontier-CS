#include <bits/stdc++.h>
using namespace std;

typedef pair<double, int> pdi;

void solve_system(double mat[60][61], double x[60]) {
    int n = 60;
    double mu = 5000.0;
    for (int i = 0; i < n; ++i) {
        int max_row = i;
        for (int k = i + 1; k < n; ++k) {
            if (fabs(mat[k][i]) > fabs(mat[max_row][i])) {
                max_row = k;
            }
        }
        for (int k = 0; k <= n; ++k) {
            swap(mat[i][k], mat[max_row][k]);
        }
        if (fabs(mat[i][i]) < 1e-12) {
            continue;
        }
        for (int k = i + 1; k < n; ++k) {
            double factor = mat[k][i] / mat[i][i];
            for (int j = i; j <= n; ++j) {
                mat[k][j] -= factor * mat[i][j];
            }
        }
    }
    for (int i = n - 1; i >= 0; --i) {
        if (fabs(mat[i][i]) < 1e-12) {
            x[i] = mu;
            continue;
        }
        double sum = mat[i][60];
        for (int j = i + 1; j < n; ++j) {
            sum -= mat[i][j] * x[j];
        }
        x[i] = sum / mat[i][i];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    double H[30], V[30];
    for (int i = 0; i < 30; ++i) {
        H[i] = 5000.0;
        V[i] = 5000.0;
    }
    double SS[60][60] = {};
    double tt[60] = {};
    double KK = 10.0;
    double mu = 5000.0;
    for (int p = 0; p < 60; ++p) {
        SS[p][p] = KK;
        tt[p] = KK * mu;
    }
    for (int q = 0; q < 1000; ++q) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;
        int sid = si * 30 + sj;
        int tid = ti * 30 + tj;
        vector<double> dist(900, 1e18);
        dist[sid] = 0.0;
        vector<int> prevv(900, -1);
        priority_queue<pdi, vector<pdi>, greater<pdi>> pq;
        pq.push({0.0, sid});
        while (!pq.empty()) {
            auto [cost, u] = pq.top(); pq.pop();
            if (cost > dist[u]) continue;
            int i = u / 30, j = u % 30;
            vector<pair<int, double>> dirs = {
                {i * 30 + (j + 1), H[i]},
                {i * 30 + (j - 1), H[i]},
                {(i + 1) * 30 + j, V[j]},
                {(i - 1) * 30 + j, V[j]}
            };
            for (auto [v, w] : dirs) {
                int ni = v / 30, nj = v % 30;
                if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) continue;
                double alt = dist[u] + w;
                if (alt < dist[v]) {
                    dist[v] = alt;
                    prevv[v] = u;
                    pq.push({alt, v});
                }
            }
        }
        vector<int> path;
        for (int at = tid; at != -1; at = prevv[at]) {
            path.push_back(at);
        }
        reverse(path.begin(), path.end());
        string moves = "";
        for (size_t k = 0; k + 1 < path.size(); ++k) {
            int u = path[k], v = path[k + 1];
            int iu = u / 30, ju = u % 30;
            int iv = v / 30, jv = v % 30;
            if (iu == iv && jv == ju + 1) moves += 'R';
            else if (iu == iv && jv == ju - 1) moves += 'L';
            else if (iv == iu + 1 && ju == jv) moves += 'D';
            else if (iv == iu - 1 && ju == jv) moves += 'U';
        }
        cout << moves << '\n';
        cout.flush();
        int c;
        cin >> c;
        double cc = (double)c;
        vector<double> aa(60, 0.0);
        for (size_t k = 0; k + 1 < path.size(); ++k) {
            int u = path[k], v = path[k + 1];
            int iu = u / 30, ju = u % 30;
            int iv = v / 30, jv = v % 30;
            if (iu == iv) {
                aa[iu] += 1.0;
            } else {
                aa[30 + ju] += 1.0;
            }
        }
        for (int p = 0; p < 60; ++p) {
            for (int r = 0; r < 60; ++r) {
                SS[p][r] += aa[p] * aa[r];
            }
            tt[p] += aa[p] * cc;
        }
        double mat[60][61];
        for (int i = 0; i < 60; ++i) {
            for (int j = 0; j < 60; ++j) mat[i][j] = SS[i][j];
            mat[i][60] = tt[i];
        }
        double xx[60];
        solve_system(mat, xx);
        for (int i = 0; i < 30; ++i) H[i] = xx[i];
        for (int i = 0; i < 30; ++i) V[i] = xx[30 + i];
    }
    return 0;
}