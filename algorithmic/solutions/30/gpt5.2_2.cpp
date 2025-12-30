#include <bits/stdc++.h>
using namespace std;

static inline bool isInSubtree(int v, int x, const vector<int>& tin, const vector<int>& tout) {
    return tin[x] <= tin[v] && tin[v] <= tout[x];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> parent(n + 1, 0), depth(n + 1, 0), tin(n + 1, 0), tout(n + 1, 0);
        vector<int> order;
        order.reserve(n);

        // Iterative DFS from root 1 to build parent/depth and Euler tin/tout (tout as max tin in subtree)
        int timer = 0;
        vector<int> it(n + 1, 0);
        vector<int> st;
        st.reserve(n);
        st.push_back(1);
        parent[1] = 0;
        depth[1] = 0;

        while (!st.empty()) {
            int v = st.back();
            if (it[v] == 0) {
                tin[v] = ++timer;
                order.push_back(v);
            }
            if (it[v] < (int)g[v].size()) {
                int to = g[v][it[v]++];
                if (to == parent[v]) continue;
                parent[to] = v;
                depth[to] = depth[v] + 1;
                st.push_back(to);
            } else {
                tout[v] = timer;
                st.pop_back();
            }
        }

        vector<vector<int>> children(n + 1);
        for (int v = 2; v <= n; v++) children[parent[v]].push_back(v);

        vector<int> cand(n);
        iota(cand.begin(), cand.end(), 1);

        vector<int> subtreeSum(n + 1, 0);
        vector<unsigned char> w(n + 1, 0);
        vector<int> mark(n + 1, 0);
        int stamp = 1;

        int queries = 0;

        while ((int)cand.size() > 1) {
            if (queries >= 160) return 0;

            int total = (int)cand.size();
            fill(w.begin(), w.end(), 0);
            for (int v : cand) w[v] = 1;

            // Compute subtree sums of candidate weights
            fill(subtreeSum.begin(), subtreeSum.end(), 0);
            for (int i = (int)order.size() - 1; i >= 0; i--) {
                int v = order[i];
                int sum = (int)w[v];
                for (int c : children[v]) sum += subtreeSum[c];
                subtreeSum[v] = sum;
            }

            int best = -1;
            int bestDiff = INT_MAX;
            int bestDepth = INT_MAX;

            for (int v = 2; v <= n; v++) {
                int s = subtreeSum[v];
                if (s > 0 && s < total) {
                    int diff = abs(total - 2 * s);
                    if (diff < bestDiff || (diff == bestDiff && depth[v] < bestDepth)) {
                        bestDiff = diff;
                        bestDepth = depth[v];
                        best = v;
                    }
                }
            }
            if (best == -1) {
                for (int v : cand) {
                    if (v != 1) {
                        best = v;
                        break;
                    }
                }
                if (best == -1) best = 1;
            }

            cout << "? " << best << "\n";
            cout.flush();

            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            queries++;

            vector<int> newCand;
            newCand.reserve(cand.size());

            if (ans == 1) {
                for (int v : cand) {
                    if (isInSubtree(v, best, tin, tout)) newCand.push_back(v);
                }
            } else {
                if (++stamp == INT_MAX) {
                    fill(mark.begin(), mark.end(), 0);
                    stamp = 1;
                }
                for (int v : cand) {
                    if (!isInSubtree(v, best, tin, tout)) {
                        int u = (v == 1 ? 1 : parent[v]);
                        if (mark[u] != stamp) {
                            mark[u] = stamp;
                            newCand.push_back(u);
                        }
                    }
                }
            }

            cand.swap(newCand);
        }

        cout << "! " << cand[0] << "\n";
        cout.flush();
    }

    return 0;
}