#include <bits/stdc++.h>
using namespace std;

int main() {
    int h;
    scanf("%d", &h);
    long long n = (1LL << h) - 1;
    vector<vector<int>> adj(n + 1);
    for (long long u = 1; u <= n / 2; ++u) {
        long long l = 2 * u;
        long long r = 2 * u + 1;
        if (l <= n) {
            adj[u].push_back(l);
            adj[l].push_back(u);
        }
        if (r <= n) {
            adj[u].push_back(r);
            adj[r].push_back(u);
        }
    }
    int maxd = 2 * h;
    vector<vector<long long>> num(h, vector<long long>(maxd + 1, 0));
    for (int l = 0; l < h; ++l) {
        int v = 1 << l;
        vector<int> dist(n + 1, -1);
        queue<int> q;
        q.push(v);
        dist[v] = 0;
        while (!q.empty()) {
            int cur = q.front();
            q.pop();
            for (int nei : adj[cur]) {
                if (dist[nei] == -1) {
                    dist[nei] = dist[cur] + 1;
                    q.push(nei);
                }
            }
        }
        for (int i = 1; i <= n; ++i) {
            int d = dist[i];
            if (d != -1 && d <= maxd) {
                num[l][d]++;
            }
        }
    }
    vector<int> ks(h);
    for (int m = 1; m <= h; ++m) {
        ks[m - 1] = 2 * h - m - 1;
    }
    vector<long long> Ts(h, 0);
    for (int i = 0; i < h; ++i) {
        int dd = ks[i];
        long long sumt = 0;
        for (long long u = 1; u <= n; ++u) {
            printf("? %lld %d\n", u, dd);
            fflush(stdout);
            long long res;
            scanf("%lld", &res);
            sumt += res;
        }
        Ts[i] = sumt;
    }
    vector<long long> level_sum(h, 0);
    // First, level h-1, m=1, i=0
    int bot = h - 1;
    int kk = ks[0];
    long long denom = num[bot][kk];
    level_sum[bot] = Ts[0] / denom;
    // Now for mm=2 to h
    for (int mm = 2; mm <= h; ++mm) {
        int target_lev = h - mm;
        int ii = mm - 1;
        kk = ks[ii];
        long long curr_t = Ts[ii];
        for (int known_lev = target_lev + 1; known_lev <= h - 1; ++known_lev) {
            curr_t -= level_sum[known_lev] * num[known_lev][kk];
        }
        denom = num[target_lev][kk];
        level_sum[target_lev] = curr_t / denom;
    }
    long long S = 0;
    for (int l = 0; l < h; ++l) {
        S += level_sum[l];
    }
    printf("! %lld\n", S);
    fflush(stdout);
    return 0;
}