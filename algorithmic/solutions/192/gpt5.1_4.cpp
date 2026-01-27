#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue; // though problem states no self-loops
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }

    vector<int> deg(n);
    for (int i = 0; i < n; ++i) {
        deg[i] = (int)adj[i].size();
    }

    using Clock = chrono::steady_clock;
    auto startTime = Clock::now();
    const double TIME_LIMIT = 0.8; // seconds, heuristic

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> side(n), bestSide(n, 0), oppCnt(n), delta(n);

    int bestCut = 0; // all-zero partition has cut 0

    const double T0 = 2.5;
    const double T_end = 0.01;
    const int targetTotalSteps = 2000000;
    double alpha = pow(T_end / T0, 1.0 / targetTotalSteps);

    while (true) {
        double elapsed = chrono::duration<double>(Clock::now() - startTime).count();
        if (elapsed > TIME_LIMIT) break;

        // Random initial partition
        for (int i = 0; i < n; ++i) {
            side[i] = rng() & 1;
        }

        int curCut = 0;
        for (const auto &e : edges) {
            if (side[e.first] != side[e.second]) ++curCut;
        }

        // Initialize oppCnt and delta
        for (int u = 0; u < n; ++u) {
            int cnt = 0;
            for (int v : adj[u]) {
                if (side[v] != side[u]) ++cnt;
            }
            oppCnt[u] = cnt;
            delta[u] = deg[u] - 2 * cnt;
        }

        if (curCut > bestCut) {
            bestCut = curCut;
            bestSide = side;
        }

        double T = T0;
        int innerIters = 0;
        const int MAX_INNER_ITERS = 200000;

        while (innerIters < MAX_INNER_ITERS) {
            if ((innerIters & 0x3FFF) == 0) { // periodic time check
                double elapsed2 = chrono::duration<double>(Clock::now() - startTime).count();
                if (elapsed2 > TIME_LIMIT) goto END_SA;
            }

            int v = (int)(rng() % n);
            int g = delta[v];
            bool accept = false;

            if (g >= 0) {
                accept = true;
            } else {
                double prob = exp((double)g / T);
                double r = (double)rng() / rng.max();
                if (r < prob) accept = true;
            }

            if (accept) {
                int oldSide = side[v];
                side[v] = 1 - oldSide;
                curCut += g;

                // Update v
                oppCnt[v] = deg[v] - oppCnt[v];
                delta[v] = -g;

                // Update neighbors
                for (int u : adj[v]) {
                    if (side[u] == oldSide) {
                        // edge was same, now opposite
                        ++oppCnt[u];
                    } else {
                        // edge was opposite, now same
                        --oppCnt[u];
                    }
                    delta[u] = deg[u] - 2 * oppCnt[u];
                }

                if (curCut > bestCut) {
                    bestCut = curCut;
                    bestSide = side;
                }
            }

            T *= alpha;
            if (T < T_end) T = T_end;
            ++innerIters;
        }
    }

END_SA:;

    // Final greedy hill-climbing from bestSide
    side = bestSide;
    int curCut = 0;
    for (const auto &e : edges) {
        if (side[e.first] != side[e.second]) ++curCut;
    }
    for (int u = 0; u < n; ++u) {
        int cnt = 0;
        for (int v : adj[u]) {
            if (side[v] != side[u]) ++cnt;
        }
        oppCnt[u] = cnt;
        delta[u] = deg[u] - 2 * cnt;
    }

    while (true) {
        double elapsed = chrono::duration<double>(Clock::now() - startTime).count();
        if (elapsed > 0.98) break; // safety margin

        int bestV = -1;
        int bestG = 0;
        for (int i = 0; i < n; ++i) {
            if (delta[i] > bestG) {
                bestG = delta[i];
                bestV = i;
            }
        }
        if (bestG <= 0 || bestV == -1) break;

        int v = bestV;
        int g = bestG;
        int oldSide = side[v];
        side[v] = 1 - oldSide;
        curCut += g;

        oppCnt[v] = deg[v] - oppCnt[v];
        delta[v] = -g;

        for (int u : adj[v]) {
            if (side[u] == oldSide) {
                ++oppCnt[u];
            } else {
                --oppCnt[u];
            }
            delta[u] = deg[u] - 2 * oppCnt[u];
        }
    }

    if (curCut > bestCut) {
        bestCut = curCut;
        bestSide = side;
    }

    for (int i = 0; i < n; ++i) {
        cout << bestSide[i] << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}