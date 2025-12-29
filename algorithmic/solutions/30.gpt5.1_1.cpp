#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // Precompute parent, depth, tin, tout, and DFS order
        vector<int> parent(n + 1), depth(n + 1), tin(n + 1), tout(n + 1), order;
        order.reserve(n);
        int timer = 0;
        function<void(int, int)> dfs = [&](int u, int p) {
            parent[u] = p;
            depth[u] = (p == 0 ? 0 : depth[p] + 1);
            tin[u] = ++timer;
            order.push_back(u);
            for (int v : adj[u]) {
                if (v == p) continue;
                dfs(v, u);
            }
            tout[u] = timer;
        };
        dfs(1, 0);

        auto inSubtree = [&](int v, int x) -> bool {
            return tin[x] <= tin[v] && tin[v] <= tout[x];
        };

        // Candidate set of possible current mole positions
        vector<int> S;
        S.reserve(n);
        for (int i = 1; i <= n; ++i) S.push_back(i);

        int queryCnt = 0;

        auto ask = [&](int x) -> int {
            cout << "? " << x << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) exit(0);
            ++queryCnt;
            return ans;
        };

        while (S.size() > 1 && queryCnt < 160) {
            int k = (int)S.size();

            // Mark current candidates
            vector<int> mark(n + 1, 0);
            for (int v : S) mark[v] = 1;

            // Compute subtree candidate counts for each node
            vector<int> sub(n + 1, 0);
            for (int i = n - 1; i >= 0; --i) {
                int u = order[i];
                int sum = mark[u];
                for (int v : adj[u]) {
                    if (v == parent[u]) continue;
                    sum += sub[v];
                }
                sub[u] = sum;
            }

            // Find a node giving the best static split
            int bestSplit = -1;
            int bestValue = k + 1;
            for (int u = 1; u <= n; ++u) {
                int s = sub[u];
                if (s == 0 || s == k) continue;
                int val = max(s, k - s);
                if (val < bestValue) {
                    bestValue = val;
                    bestSplit = u;
                }
            }

            // Count how many candidate children each parent has
            vector<int> childCnt(n + 1, 0);
            for (int v : S) {
                int p = parent[v];
                if (p != 0) ++childCnt[p];
            }
            int p_best = -1, maxChildCnt = 0;
            for (int v = 1; v <= n; ++v) {
                if (childCnt[v] > maxChildCnt) {
                    maxChildCnt = childCnt[v];
                    p_best = v;
                }
            }

            int x_split = bestSplit;
            int x_merge = -1;
            if (p_best != -1 && maxChildCnt >= 2) {
                int bestChild = -1;
                int bestSubVal = INT_MAX;
                for (int v : S) {
                    if (parent[v] == p_best) {
                        if (sub[v] < bestSubVal) {
                            bestSubVal = sub[v];
                            bestChild = v;
                        }
                    }
                }
                if (bestChild != -1) x_merge = bestChild;
            }

            int x;
            if (x_merge == -1) {
                x = x_split;
            } else {
                auto computeBeta = [&](int xnode) -> int {
                    int size1 = 0;
                    for (int v : S) {
                        if (inSubtree(v, xnode)) ++size1;
                    }
                    static vector<char> vis;
                    if ((int)vis.size() < n + 1) vis.assign(n + 1, 0);
                    else fill(vis.begin(), vis.end(), 0);
                    int size0 = 0;
                    for (int v : S) {
                        if (inSubtree(v, xnode)) continue;
                        int p = (v == 1 ? 1 : parent[v]);
                        if (!vis[p]) {
                            vis[p] = 1;
                            ++size0;
                        }
                    }
                    return max(size1, size0);
                };
                int beta_split = (x_split != -1 ? computeBeta(x_split) : INT_MAX);
                int beta_merge = computeBeta(x_merge);
                if (beta_merge < beta_split) x = x_merge;
                else x = x_split;
            }

            if (x == -1) x = 1;  // Fallback (should not happen)

            int ans = ask(x);

            if (ans == 1) {
                vector<int> newS;
                newS.reserve(S.size());
                for (int v : S) {
                    if (inSubtree(v, x)) newS.push_back(v);
                }
                S.swap(newS);
            } else {
                vector<int> newSpos;
                newSpos.reserve(S.size());
                vector<char> vis(n + 1, 0);
                for (int v : S) {
                    if (inSubtree(v, x)) continue;
                    int p = (v == 1 ? 1 : parent[v]);
                    if (!vis[p]) {
                        vis[p] = 1;
                        newSpos.push_back(p);
                    }
                }
                S.swap(newSpos);
            }
        }

        int ansNode = S.empty() ? 1 : S[0];
        cout << "! " << ansNode << endl;
        cout.flush();
    }

    return 0;
}