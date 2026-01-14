#include <bits/stdc++.h>
using namespace std;

vector<double> solve(vector<vector<double>> a, vector<double> b) {
    int n = a.size();
    for (int i = 0; i < n; ++i) {
        int maxj = i;
        for (int j = i + 1; j < n; ++j) {
            if (abs(a[j][i]) > abs(a[maxj][i])) maxj = j;
        }
        swap(a[i], a[maxj]);
        swap(b[i], b[maxj]);
        if (abs(a[i][i]) < 1e-10) {
            // singular, assume not
            continue;
        }
        for (int j = i + 1; j < n; ++j) {
            double c = -a[j][i] / a[i][i];
            for (int k = i; k < n; ++k) {
                if (i == k) a[j][k] = 0.0;
                else a[j][k] += c * a[i][k];
            }
            b[j] += c * b[i];
        }
    }
    vector<double> x(n);
    for (int i = n - 1; i >= 0; --i) {
        x[i] = b[i];
        for (int j = i + 1; j < n; ++j) x[i] -= a[i][j] * x[j];
        if (abs(a[i][i]) > 1e-10) x[i] /= a[i][i];
    }
    return x;
}

int main() {
    int h;
    scanf("%d", &h);
    long long nn = (1LL << h) - 1;
    int N = (int) nn;
    vector<vector<int>> adj(N + 1);
    for (int i = 1; i <= N / 2; ++i) {
        adj[i].push_back(2 * i);
        adj[2 * i].push_back(i);
        int rr = 2 * i + 1;
        if (rr <= N) {
            adj[i].push_back(rr);
            adj[rr].push_back(i);
        }
    }
    int max_dist = 2 * (h - 1);
    vector<vector<long long>> g(max_dist + 1, vector<long long>(h, 0LL));
    for (int dep = 0; dep < h; ++dep) {
        int start = 1 << dep;
        vector<int> dist(N + 1, -1);
        queue<int> q;
        q.push(start);
        dist[start] = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        vector<long long> cnt(max_dist + 1, 0);
        for (int node = 1; node <= N; ++node) {
            int d = dist[node];
            if (d >= 0 && d <= max_dist) ++cnt[d];
        }
        for (int k = 0; k <= max_dist; ++k) {
            g[k][dep] = cnt[k];
        }
    }
    int rr = h;
    vector<int> ks(rr);
    for (int i = 0; i < rr; ++i) ks[i] = i + 1;
    vector<vector<double>> AA(rr, vector<double>(h));
    for (int i = 0; i < rr; ++i) {
        int kk = ks[i];
        for (int j = 0; j < h; ++j) {
            AA[i][j] = (double) g[kk][j];
        }
    }
    vector<long long> QQ(rr, 0LL);
    for (int i = 0; i < rr; ++i) {
        int kk = ks[i];
        for (int u = 1; u <= N; ++u) {
            printf("? %d %d\n", u, kk);
            fflush(stdout);
            long long resp;
            scanf("%lld", &resp);
            QQ[i] += resp;
        }
    }
    vector<double> bb(rr);
    for (int i = 0; i < rr; ++i) bb[i] = (double) QQ[i];
    vector<double> svec = solve(AA, bb);
    long long S = 0;
    for (double v : svec) {
        S += llround(v);
    }
    printf("! %lld\n", S);
    fflush(stdout);
    return 0;
}