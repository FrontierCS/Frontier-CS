#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    const int COLORS = 3;
    using Arr3 = array<int, 3>;

    vector<int> bestColors(n, 0);
    long long bestConf = LLONG_MAX;

    vector<Arr3> cnt(n);
    vector<int> curColors(n);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    const int maxSweeps = 20;
    const long long maxWork = 200000000LL; // ~2e8 basic units

    int restarts = (int)(maxWork / (maxSweeps * max(1LL, m)));
    if (restarts < 1) restarts = 1;
    if (restarts > 50) restarts = 50;

    auto startTime = chrono::steady_clock::now();
    const double timeLimit = 0.95; // seconds

    for (int iter = 0; iter < restarts; ++iter) {
        // Random initial colors and reset counts
        for (int v = 0; v < n; ++v) {
            curColors[v] = rng() % COLORS;
            cnt[v] = {0, 0, 0};
        }

        // Build neighbor color counts
        for (int v = 0; v < n; ++v) {
            for (int u : adj[v]) {
                int cu = curColors[u];
                cnt[v][cu]++;
            }
        }

        // Compute initial number of conflicting edges
        long long curConf = 0;
        for (int v = 0; v < n; ++v) {
            curConf += cnt[v][curColors[v]];
        }
        curConf /= 2;

        bool improved = true;
        for (int sweep = 0; sweep < maxSweeps && improved; ++sweep) {
            improved = false;
            shuffle(order.begin(), order.end(), rng);

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                int curC = curColors[v];
                int curBad = cnt[v][curC];

                int bestC = curC;
                int bestBad = curBad;

                for (int c = 0; c < COLORS; ++c) {
                    if (c == curC) continue;
                    int bad = cnt[v][c];
                    if (bad < bestBad) {
                        bestBad = bad;
                        bestC = c;
                    }
                }

                if (bestC != curC) {
                    long long delta = (long long)bestBad - (long long)curBad;
                    curConf += delta;

                    // Update neighbors' counts
                    for (int u : adj[v]) {
                        cnt[u][curC]--;
                        cnt[u][bestC]++;
                    }

                    curColors[v] = bestC;
                    improved = true;

                    if (curConf == 0) break;
                }
            }

            if (curConf == 0) break;

            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            if (elapsed > timeLimit) break;
        }

        if (curConf < bestConf) {
            bestConf = curConf;
            bestColors = curColors;
            if (bestConf == 0) break;
        }

        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > timeLimit) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestColors[i] + 1);
    }
    cout << '\n';

    return 0;
}