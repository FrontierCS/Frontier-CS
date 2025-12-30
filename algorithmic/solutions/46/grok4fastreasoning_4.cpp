#include <bits/stdc++.h>
using namespace std;

int main() {
    int J, M;
    cin >> J >> M;
    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<int>> proc(J, vector<int>(M));
    vector<vector<int>> pos_of(J, vector<int>(M, -1));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m, p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
            pos_of[j][m] = k;
        }
    }
    vector<long long> total(J, 0);
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            total[j] += proc[j][k];
        }
    }
    vector<int> pi(J);
    iota(pi.begin(), pi.end(), 0);
    sort(pi.begin(), pi.end(), [&](int a, int b) {
        return total[a] < total[b] || (total[a] == total[b] && a < b);
    });
    vector<vector<int>> current(M, vector<int>(J));
    for (int m = 0; m < M; m++) {
        current[m] = pi;
    }
    auto compute = [&](const vector<vector<int>>& ord) -> long long {
        int N = J * M;
        vector<vector<pair<int, long long>>> g(N);
        for (int jj = 0; jj < J; jj++) {
            for (int kk = 0; kk < M - 1; kk++) {
                int u = jj * M + kk;
                int v = jj * M + kk + 1;
                g[u].emplace_back(v, proc[jj][kk]);
            }
        }
        for (int mm = 0; mm < M; mm++) {
            for (int ii = 0; ii < J - 1; ii++) {
                int ja = ord[mm][ii];
                int jb = ord[mm][ii + 1];
                int posa = pos_of[ja][mm];
                int posb = pos_of[jb][mm];
                int u = ja * M + posa;
                int v = jb * M + posb;
                g[u].emplace_back(v, (long long)proc[ja][posa]);
            }
        }
        vector<int> indeg(N, 0);
        for (int u = 0; u < N; u++) {
            for (auto& pr : g[u]) {
                indeg[pr.first]++;
            }
        }
        queue<int> q;
        for (int u = 0; u < N; u++) {
            if (indeg[u] == 0) q.push(u);
        }
        vector<long long> S(N, 0LL);
        int vis = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            vis++;
            for (auto& pr : g[u]) {
                int v = pr.first;
                long long w = pr.second;
                S[v] = max(S[v], S[u] + w);
                if (--indeg[v] == 0) q.push(v);
            }
        }
        if (vis < N) return -1LL;
        long long ms = 0;
        for (int jj = 0; jj < J; jj++) {
            for (int kk = 0; kk < M; kk++) {
                int o = jj * M + kk;
                ms = max(ms, S[o] + proc[jj][kk]);
            }
        }
        return ms;
    };
    long long best_ms = compute(current);
    bool improved = true;
    int iter = 0;
    const int max_iter = 1000;
    while (improved && iter++ < max_iter) {
        improved = false;
        for (int m = 0; m < M; m++) {
            for (int i = 0; i < J - 1; i++) {
                swap(current[m][i], current[m][i + 1]);
                long long news = compute(current);
                if (news != -1 && news < best_ms) {
                    best_ms = news;
                    improved = true;
                } else {
                    swap(current[m][i], current[m][i + 1]);
                }
            }
        }
    }
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i > 0) cout << " ";
            cout << current[m][i];
        }
        cout << endl;
    }
    return 0;
}