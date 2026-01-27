#include <bits/stdc++.h>
using namespace std;

struct HopcroftKarp {
    int nL, nR;
    vector<vector<int>> adj;
    vector<int> dist, pairU, pairV;

    HopcroftKarp(int _nL, int _nR) : nL(_nL), nR(_nR) {
        adj.assign(nL + 1, {});
        pairU.assign(nL + 1, 0);
        pairV.assign(nR + 1, 0);
        dist.assign(nL + 1, 0);
    }

    void addEdge(int u, int v) { // u in [1..nL], v in [1..nR]
        adj[u].push_back(v);
    }

    bool bfs() {
        queue<int> q;
        const int INF = 1e9;
        for (int u = 1; u <= nL; ++u) {
            if (pairU[u] == 0) {
                dist[u] = 0;
                q.push(u);
            } else {
                dist[u] = INF;
            }
        }
        bool reachableFree = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                int mu = pairV[v];
                if (mu == 0) {
                    reachableFree = true;
                } else if (dist[mu] == INF) {
                    dist[mu] = dist[u] + 1;
                    q.push(mu);
                }
            }
        }
        return reachableFree;
    }

    bool dfs(int u) {
        for (int v : adj[u]) {
            int mu = pairV[v];
            if (mu == 0 || (dist[mu] == dist[u] + 1 && dfs(mu))) {
                pairU[u] = v;
                pairV[v] = u;
                return true;
            }
        }
        dist[u] = INT_MAX;
        return false;
    }

    int maxMatching() {
        int matching = 0;
        while (bfs()) {
            for (int u = 1; u <= nL; ++u) {
                if (pairU[u] == 0 && dfs(u)) {
                    matching++;
                }
            }
        }
        return matching;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int S = n + 1;
    vector<vector<int>> a(n + 2); // 1..n tubes, S is spare
    vector<vector<int>> present(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        a[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            a[i].push_back(c);
            present[c][i] = 1;
        }
    }
    // Build matching: colors (1..n) -> tubes (1..n) where color appears
    HopcroftKarp hk(n, n);
    for (int c = 1; c <= n; ++c) {
        for (int t = 1; t <= n; ++t) {
            if (present[c][t]) hk.addEdge(c, t);
        }
    }
    int match = hk.maxMatching();
    // By capacity argument, perfect matching must exist
    // But to be safe, if not, fall back to any assignment (shouldn't happen)
    if (match < n) {
        // Fallback trivial mapping (1->1,2->2,...) ensures correctness still reachable by algorithm
        for (int c = 1; c <= n; ++c) {
            hk.pairU[c] = c;
            hk.pairV[c] = c;
        }
    }
    vector<int> home(n + 1, 0);         // home[color] = tube
    vector<int> targetColor(n + 2, 0);  // targetColor[tube] = color assigned to tube
    for (int c = 1; c <= n; ++c) {
        home[c] = hk.pairU[c];
        targetColor[home[c]] = c;
    }

    // Prepare counts
    vector<int> cap(n + 2, 0);
    vector<int> wrongCount(n + 2, 0);
    long long totalWrong = 0;
    for (int i = 1; i <= n; ++i) {
        cap[i] = (int)a[i].size();
        int cnt = 0;
        for (int x : a[i]) if (x != targetColor[i]) cnt++;
        wrongCount[i] = cnt;
        totalWrong += cnt;
    }
    cap[S] = (int)a[S].size();

    vector<pair<int,int>> ops;
    ops.reserve((size_t) (n * m * 5));

    auto moveBall = [&](int x, int y) {
        int c = a[x].back();
        a[x].pop_back();
        cap[x]--;
        if (x <= n) {
            if (c != targetColor[x]) {
                wrongCount[x]--;
                totalWrong--;
            }
        }
        a[y].push_back(c);
        cap[y]++;
        if (y <= n) {
            if (c != targetColor[y]) {
                wrongCount[y]++;
                totalWrong++;
            }
        }
        ops.emplace_back(x, y);
    };

    // Main process
    while (totalWrong > 0) {
        bool progressed = false;

        // Drain spare to home as much as possible
        while (!a[S].empty()) {
            int c = a[S].back();
            int j = home[c];
            if (cap[j] < m) {
                moveBall(S, j);
                progressed = true;
            } else break;
        }
        if (progressed) continue;

        // Direct move: top -> home if dest has space
        for (int i = 1; i <= n && !progressed; ++i) {
            if (cap[i] == 0) continue;
            int c = a[i].back();
            int j = home[c];
            if (i != j && cap[j] < m) {
                moveBall(i, j);
                progressed = true;
            }
        }
        if (progressed) continue;

        // Fallback Case A: find top not in its home, free space in its home by moving one from home to spare, then move it
        int i_not_home = -1;
        for (int i = 1; i <= n; ++i) {
            if (cap[i] == 0) continue;
            int c = a[i].back();
            if (home[c] != i) { i_not_home = i; break; }
        }
        if (i_not_home != -1) {
            int c = a[i_not_home].back();
            int j = home[c];
            // j must be full, otherwise we'd have moved directly
            // free one spot in j
            moveBall(j, S);
            moveBall(i_not_home, j);
            continue;
        }

        // Fallback Case B: All tops are in their homes but not finished. Create a mismatch by rotating.
        int aidx = -1;
        for (int i = 1; i <= n; ++i) {
            if (wrongCount[i] > 0) { aidx = i; break; }
        }
        // It should exist since totalWrong > 0
        if (aidx == -1) {
            // Should not happen, but to avoid infinite loop, break.
            break;
        }
        int bidx = (aidx % n) + 1;
        if (bidx == aidx) bidx = (bidx % n) + 1;
        // aidx has at least one ball, since wrongCount>0 implies cap>0
        moveBall(aidx, S);
        moveBall(bidx, aidx);
    }

    // After organizing, ensure spare is empty (should be)
    while (!a[S].empty()) {
        int c = a[S].back();
        int j = home[c];
        // There must be space
        if (cap[j] < m) {
            moveBall(S, j);
        } else {
            // Free one from j if needed
            moveBall(j, S);
        }
    }

    cout << ops.size() << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}