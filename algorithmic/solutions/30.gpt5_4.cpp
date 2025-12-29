#include <bits/stdc++.h>
using namespace std;

int n, tcase_n;
vector<vector<int>> g;
vector<int> parent_, depth_, tin, tout;
int timer_ = 0;

void dfs(int u, int p) {
    parent_[u] = p;
    tin[u] = ++timer_;
    for (int v : g[u]) {
        if (v == p) continue;
        depth_[v] = depth_[u] + 1;
        dfs(v, u);
    }
    tout[u] = timer_;
}

inline bool in_subtree(int u, int x) {
    return tin[x] <= tin[u] && tin[u] <= tout[x];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        cin >> n;
        g.assign(n + 1, {});
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        parent_.assign(n + 1, 0);
        depth_.assign(n + 1, 0);
        tin.assign(n + 1, 0);
        tout.assign(n + 1, 0);
        timer_ = 0;
        dfs(1, 0);

        vector<char> alive(n + 1, 1);
        vector<int> pos(n + 1, 0);
        for (int s = 1; s <= n; ++s) pos[s] = s;

        int aliveCount = n;
        int queryCount = 0;

        while (true) {
            // Check if all current positions are the same
            int curPos = -1;
            bool allSame = true;
            for (int s = 1; s <= n; ++s) if (alive[s]) { curPos = pos[s]; break; }
            for (int s = 1; s <= n; ++s) if (alive[s]) {
                if (pos[s] != curPos) { allSame = false; break; }
            }
            if (allSame) {
                cout << "! " << curPos << endl;
                cout.flush();
                break;
            }

            // Build counts of current positions
            vector<int> cntPos(n + 1, 0);
            for (int s = 1; s <= n; ++s) if (alive[s]) cntPos[pos[s]]++;

            // Build prefix over Euler tour
            vector<int> eulerCnt(n + 2, 0);
            for (int u = 1; u <= n; ++u) if (cntPos[u]) eulerCnt[tin[u]] += cntPos[u];
            for (int i = 1; i <= n; ++i) eulerCnt[i] += eulerCnt[i - 1];

            // Choose best x to split
            int best_x = 1;
            int best_cost = aliveCount; // worst
            for (int x = 1; x <= n; ++x) {
                int ones = eulerCnt[tout[x]] - eulerCnt[tin[x] - 1];
                int zeros = aliveCount - ones;
                int cost = max(ones, zeros);
                if (cost < best_cost) {
                    best_cost = cost;
                    best_x = x;
                }
            }

            cout << "? " << best_x << endl;
            cout.flush();
            queryCount++;
            int r;
            if (!(cin >> r)) return 0;
            if (r == -1) return 0;

            // Filter alive based on response using positions BEFORE movement
            for (int s = 1; s <= n; ++s) if (alive[s]) {
                if ((int)in_subtree(pos[s], best_x) != r) {
                    alive[s] = 0;
                    aliveCount--;
                }
            }

            // Apply movement after response
            if (r == 0) {
                for (int s = 1; s <= n; ++s) if (alive[s]) {
                    if (pos[s] != 1) pos[s] = parent_[pos[s]];
                }
            }

            if (queryCount >= 160) {
                // To comply with the problem statement, terminate immediately if exceeding limit
                return 0;
            }
        }
    }
    return 0;
}