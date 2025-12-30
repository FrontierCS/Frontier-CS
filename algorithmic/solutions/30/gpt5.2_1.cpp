#include <bits/stdc++.h>
using namespace std;

static inline void flush_out() { cout.flush(); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        vector<int> parent(n + 1, 1), depth(n + 1, 0);
        vector<int> tin(n + 1, 0), tout(n + 1, 0), euler(n + 1, 0);

        // Iterative DFS for tin/tout/parent/depth
        int timer = 0;
        vector<int> it(n + 1, 0);
        stack<int> st;
        st.push(1);
        parent[1] = 1;
        depth[1] = 0;

        while (!st.empty()) {
            int u = st.top();
            if (it[u] == 0) {
                tin[u] = ++timer;
                euler[timer] = u;
            }
            if (it[u] < (int)adj[u].size()) {
                int v = adj[u][it[u]++];
                if (v == parent[u]) continue;
                parent[v] = u;
                depth[v] = depth[u] + 1;
                st.push(v);
            } else {
                tout[u] = timer;
                st.pop();
            }
        }

        auto inSubtree = [&](int x, int v) -> bool {
            return tin[x] <= tin[v] && tin[v] <= tout[x];
        };

        vector<int> cand;
        cand.reserve(n);
        for (int i = 1; i <= n; i++) cand.push_back(i);

        int qcnt = 0;

        vector<char> inCand(n + 1, 0);
        vector<int> prefCand(n + 1, 0), prefLca(n + 1, 0);
        vector<int> cntPar(n + 1, 0), singleNode(n + 1, 0), lcaCount(n + 1, 0);
        vector<char> seen(n + 1, 0);

        while ((int)cand.size() > 1) {
            if (qcnt >= 160) break;

            int m = (int)cand.size();

            fill(inCand.begin(), inCand.end(), 0);
            for (int v : cand) inCand[v] = 1;

            prefCand[0] = 0;
            for (int i = 1; i <= n; i++) {
                prefCand[i] = prefCand[i - 1] + (inCand[euler[i]] ? 1 : 0);
            }
            auto subCandCount = [&](int x) -> int {
                return prefCand[tout[x]] - prefCand[tin[x] - 1];
            };

            fill(cntPar.begin(), cntPar.end(), 0);
            // singleNode doesn't need full clear; only valid when cntPar==1, but set anyway for visited parents
            for (int v : cand) {
                int p = parent[v];
                cntPar[p]++;
                singleNode[p] = v;
            }

            fill(lcaCount.begin(), lcaCount.end(), 0);
            int activeParents = 0;
            for (int p = 1; p <= n; p++) {
                if (cntPar[p] == 0) continue;
                activeParents++;
                int l = (cntPar[p] == 1) ? singleNode[p] : p; // LCA of >=2 children of p is p itself
                lcaCount[l]++;
            }

            prefLca[0] = 0;
            for (int i = 1; i <= n; i++) {
                prefLca[i] = prefLca[i - 1] + lcaCount[euler[i]];
            }
            auto subLcaCount = [&](int x) -> int {
                return prefLca[tout[x]] - prefLca[tin[x] - 1];
            };

            int bestX = -1;
            int bestWorst = INT_MAX;
            int bestDepth = INT_MAX;

            for (int x = 1; x <= n; x++) {
                int s1 = subCandCount(x);
                if (s1 == m) continue; // answer 1 gives no progress
                int sL = subLcaCount(x);
                int s0 = activeParents - sL; // exact size after 0
                int worst = max(s1, s0);

                if (worst < bestWorst || (worst == bestWorst && depth[x] < bestDepth) ||
                    (worst == bestWorst && depth[x] == bestDepth && x < bestX)) {
                    bestWorst = worst;
                    bestDepth = depth[x];
                    bestX = x;
                }
            }

            if (bestX == -1) bestX = cand[0];

            cout << "? " << bestX << "\n";
            flush_out();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;

            qcnt++;
            if (qcnt > 160) return 0;

            vector<int> newCand;
            newCand.reserve(cand.size());

            if (ans == 1) {
                for (int v : cand) {
                    if (inSubtree(bestX, v)) newCand.push_back(v);
                }
            } else {
                fill(seen.begin(), seen.end(), 0);
                for (int v : cand) {
                    if (!inSubtree(bestX, v)) {
                        int p = parent[v];
                        if (!seen[p]) {
                            seen[p] = 1;
                            newCand.push_back(p);
                        }
                    }
                }
            }

            cand.swap(newCand);
            if (cand.empty()) {
                // Shouldn't happen; fallback to root to avoid UB.
                cand.push_back(1);
                break;
            }
        }

        cout << "! " << cand[0] << "\n";
        flush_out();
    }

    return 0;
}