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
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<int> deg(n);
    int maxDeg = 0;
    for (int i = 0; i < n; ++i) {
        deg[i] = (int)adj[i].size();
        if (deg[i] > maxDeg) maxDeg = deg[i];
    }

    int bucketCount = 2 * maxDeg + 1;
    int offset = maxDeg;

    vector<list<int>> buckets(bucketCount);
    vector<list<int>::iterator> itInBucket(n);
    vector<int> side(n), opp(n), gain(n);

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    int bestCut = -1;
    vector<int> bestSide(n);

    int RESTARTS = 30;

    for (int attempt = 0; attempt < RESTARTS; ++attempt) {
        // Random initial partition
        for (int i = 0; i < n; ++i) {
            side[i] = (int)(rng() & 1);
        }

        // Initialize opp and current cut value
        fill(opp.begin(), opp.end(), 0);
        int curCut = 0;
        for (const auto &e : edges) {
            int u = e.first, v = e.second;
            if (side[u] != side[v]) {
                opp[u]++;
                opp[v]++;
                curCut++;
            }
        }

        // Initialize buckets and gains
        for (int b = 0; b < bucketCount; ++b) buckets[b].clear();

        for (int v = 0; v < n; ++v) {
            gain[v] = deg[v] - 2 * opp[v];
            int idx = gain[v] + offset;
            buckets[idx].push_front(v);
            itInBucket[v] = buckets[idx].begin();
        }

        int currentMaxIdx = bucketCount - 1;
        while (currentMaxIdx > offset && buckets[currentMaxIdx].empty()) currentMaxIdx--;

        // Local search by single-vertex flips
        while (true) {
            while (currentMaxIdx > offset && buckets[currentMaxIdx].empty()) currentMaxIdx--;
            if (currentMaxIdx <= offset) break;  // no positive-gain moves

            int v = buckets[currentMaxIdx].front();
            int gOld = gain[v];  // > 0

            // Remove v from its current bucket
            buckets[currentMaxIdx].erase(itInBucket[v]);

            int oldSide = side[v];

            // Apply flip
            curCut += gOld;
            side[v] ^= 1;

            // Update v's opp and gain
            opp[v] = deg[v] - opp[v];
            int gNewv = -gOld;
            gain[v] = gNewv;
            int idxNewv = gNewv + offset;
            buckets[idxNewv].push_front(v);
            itInBucket[v] = buckets[idxNewv].begin();
            if (idxNewv > currentMaxIdx) currentMaxIdx = idxNewv;

            // Update neighbors of v
            for (int u : adj[v]) {
                int gOldu = gain[u];
                int idxOldu = gOldu + offset;

                buckets[idxOldu].erase(itInBucket[u]);

                if (side[u] == oldSide) {
                    // Edge changed from same -> opposite
                    opp[u]++;
                    gain[u] = gOldu - 2;
                } else {
                    // Edge changed from opposite -> same
                    opp[u]--;
                    gain[u] = gOldu + 2;
                }

                int idxNewu = gain[u] + offset;
                buckets[idxNewu].push_front(u);
                itInBucket[u] = buckets[idxNewu].begin();
                if (idxNewu > currentMaxIdx) currentMaxIdx = idxNewu;
            }
        }

        if (curCut > bestCut) {
            bestCut = curCut;
            bestSide = side;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestSide[i];
    }
    cout << '\n';

    return 0;
}