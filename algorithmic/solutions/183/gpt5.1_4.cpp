#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<vector<int>> adj(N + 1);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        if (u < 1 || u > N || v < 1 || v > N) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> deg(N + 1);
    for (int v = 1; v <= N; ++v) {
        deg[v] = (int)adj[v].size();
    }

    mt19937_64 rng((unsigned long long)chrono::steady_clock::now().time_since_epoch().count());

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.7; // computation time budget in seconds

    vector<unsigned char> bestSel(N + 1, 0);
    int bestK = 0;

    // Dynamic min-degree greedy MIS (with random tie-breaking)
    {
        vector<unsigned long long> randId(N + 1);
        for (int v = 1; v <= N; ++v) {
            randId[v] = rng();
        }

        vector<unsigned char> sel(N + 1, 0);
        vector<char> alive(N + 1, 1);
        vector<int> curDeg = deg;

        using Key = pair<pair<int, unsigned long long>, int>;
        priority_queue<Key, vector<Key>, greater<Key>> pq;

        for (int v = 1; v <= N; ++v) {
            pq.push({{curDeg[v], randId[v]}, v});
        }

        int K = 0;

        while (!pq.empty()) {
            auto top = pq.top();
            pq.pop();
            int v = top.second;
            int d = top.first.first;
            if (!alive[v]) continue;
            if (d != curDeg[v]) continue;

            // select v
            alive[v] = 0;
            sel[v] = 1;
            ++K;

            // remove neighbors of v and update degrees
            for (int u : adj[v]) {
                if (!alive[u]) continue;
                alive[u] = 0;
                for (int w : adj[u]) {
                    if (!alive[w]) continue;
                    --curDeg[w];
                    pq.push({{curDeg[w], randId[w]}, w});
                }
            }
        }

        bestSel = sel;
        bestK = K;
    }

    // Multi-start static-degree greedy with random tie-breaking
    vector<int> order(N);
    for (int i = 0; i < N; ++i) order[i] = i + 1;

    vector<unsigned long long> randKey(N + 1);
    vector<unsigned char> banned(N + 1);
    vector<unsigned char> curSel(N + 1);

    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT && iter > 0) break;
        if (iter > 500) break; // safety bound

        // random keys for tie-breaking
        for (int v = 1; v <= N; ++v) {
            randKey[v] = rng();
        }

        sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return randKey[a] < randKey[b];
        });

        fill(banned.begin(), banned.end(), 0);
        fill(curSel.begin(), curSel.end(), 0);
        int curK = 0;

        for (int idx = 0; idx < N; ++idx) {
            int v = order[idx];
            if (banned[v]) continue;
            curSel[v] = 1;
            ++curK;
            banned[v] = 1;
            for (int to : adj[v]) banned[to] = 1;
        }

        if (curK > bestK) {
            bestK = curK;
            bestSel = curSel;
        }

        ++iter;
    }

    for (int v = 1; v <= N; ++v) {
        cout << (bestSel[v] ? '1' : '0') << '\n';
    }

    return 0;
}