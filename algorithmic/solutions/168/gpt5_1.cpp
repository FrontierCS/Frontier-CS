#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> X(N), Y(N);
    for (int i = 0; i < N; ++i) cin >> X[i] >> Y[i];

    int mod = H + 1;

    vector<int> depth(N, -1), par(N, -1);
    vector<int> bestDepth(N, -1), bestPar(N, -1);
    long long bestScore = -1;
    int bestRoot = 0;

    deque<int> q;
    for (int r = 0; r < N; ++r) {
        fill(depth.begin(), depth.end(), -1);
        fill(par.begin(), par.end(), -1);
        depth[r] = 0;
        par[r] = -1;
        q.clear();
        q.push_back(r);
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            for (int w : adj[u]) {
                if (depth[w] == -1) {
                    depth[w] = depth[u] + 1;
                    par[w] = u;
                    q.push_back(w);
                }
            }
        }
        long long score = 0;
        for (int i = 0; i < N; ++i) {
            score += (long long)((depth[i] % mod) + 1) * (long long)A[i];
        }
        if (score > bestScore) {
            bestScore = score;
            bestDepth = depth;
            bestPar = par;
            bestRoot = r;
        }
    }

    // Cut at multiples of (H+1) depth (except the root itself)
    for (int i = 0; i < N; ++i) {
        if (i != bestRoot && bestDepth[i] % mod == 0) {
            bestPar[i] = -1;
        }
    }

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << bestPar[i];
    }
    cout << '\n';

    return 0;
}