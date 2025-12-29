#include <bits/stdc++.h>
using namespace std;

static inline void die() { exit(0); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    auto ask = [&](int x) -> int {
        cout << "? " << x << "\n";
        cout.flush();
        int r;
        if (!(cin >> r)) die();
        if (r < 0) die();
        return r;
    };

    auto answer = [&](int x) {
        cout << "! " << x << "\n";
        cout.flush();
    };

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

        vector<int> parent(n + 1, 0), depth(n + 1, 0);
        vector<int> tin(n + 1, 0), tout(n + 1, 0);
        vector<vector<int>> children(n + 1);

        // Rooted DFS from 1, iterative: compute parent/depth/tin/tout and children.
        vector<int> it(n + 1, 0);
        vector<int> st;
        st.reserve(n);
        int timer = 0;
        vector<int> ord;
        ord.reserve(n);

        parent[1] = 1;
        depth[1] = 0;
        st.push_back(1);

        while (!st.empty()) {
            int v = st.back();
            if (it[v] == 0) {
                tin[v] = ++timer;
                ord.push_back(v);
            }
            if (it[v] < (int)g[v].size()) {
                int to = g[v][it[v]++];
                if (to == parent[v]) continue;
                parent[to] = v;
                depth[to] = depth[v] + 1;
                children[v].push_back(to);
                st.push_back(to);
            } else {
                tout[v] = timer;
                st.pop_back();
            }
        }

        auto inSubtree = [&](int x, int v) -> bool {
            return tin[x] <= tin[v] && tin[v] <= tout[x];
        };

        vector<char> cand(n + 1, 1);
        int candCnt = n;

        int qcnt = 0;
        const int QLIM = 160;

        vector<int> cntSub(n + 1), parCount(n + 1), activePar(n + 1), activeSub(n + 1), onlyChild(n + 1), childFreq(n + 1);

        while (candCnt > 1) {
            if (qcnt >= QLIM) die();

            // Compute cntSub
            for (int v = 1; v <= n; v++) cntSub[v] = 0;
            for (int i = n - 1; i >= 0; i--) {
                int v = ord[i];
                int s = cand[v] ? 1 : 0;
                for (int c : children[v]) s += cntSub[c];
                cntSub[v] = s;
            }

            // Compute parCount
            fill(parCount.begin(), parCount.end(), 0);
            for (int v = 1; v <= n; v++) if (cand[v]) parCount[parent[v]]++;

            // activePar and P_all_size
            int P_all_size = 0;
            for (int p = 1; p <= n; p++) {
                activePar[p] = (parCount[p] > 0) ? 1 : 0;
                P_all_size += activePar[p];
            }

            // onlyChild + childFreq
            fill(onlyChild.begin(), onlyChild.end(), 0);
            fill(childFreq.begin(), childFreq.end(), 0);
            for (int v = 1; v <= n; v++) if (cand[v]) {
                int p = parent[v];
                if (parCount[p] == 1) onlyChild[p] = v;
            }
            for (int p = 1; p <= n; p++) if (parCount[p] == 1) {
                int c = onlyChild[p];
                if (c) childFreq[c]++;
            }

            // activeSub
            for (int i = n - 1; i >= 0; i--) {
                int v = ord[i];
                int s = activePar[v];
                for (int c : children[v]) s += activeSub[c];
                activeSub[v] = s;
            }

            // Choose query x minimizing worst possible remaining candidates count.
            int bestX = 1;
            int bestWorst = INT_MAX;
            int bestDepth = INT_MAX;

            for (int x = 1; x <= n; x++) {
                int size1 = cntSub[x];
                int size0 = P_all_size - (activeSub[x] + childFreq[x]);
                int worst;
                if (size1 == 0) worst = size0;                // answer must be 0
                else if (size1 == candCnt) worst = size1;     // answer must be 1
                else worst = max(size1, size0);

                int dx = depth[x];
                if (worst < bestWorst || (worst == bestWorst && (dx < bestDepth || (dx == bestDepth && x < bestX)))) {
                    bestWorst = worst;
                    bestDepth = dx;
                    bestX = x;
                }
            }

            int x = bestX;
            int r = ask(x);
            qcnt++;

            if (r == 1) {
                // Keep only candidates in subtree(x)
                for (int v = 1; v <= n; v++) {
                    if (cand[v] && !inSubtree(x, v)) {
                        cand[v] = 0;
                        candCnt--;
                    }
                }
            } else {
                // New candidates are parents of candidates outside subtree(x)
                vector<char> ncand(n + 1, 0);
                for (int v = 1; v <= n; v++) {
                    if (cand[v] && !inSubtree(x, v)) {
                        ncand[parent[v]] = 1;
                    }
                }
                cand.swap(ncand);
                candCnt = 0;
                for (int v = 1; v <= n; v++) if (cand[v]) candCnt++;
                if (candCnt == 0) { // safety, should never happen
                    cand[1] = 1;
                    candCnt = 1;
                }
            }
        }

        int res = 1;
        for (int v = 1; v <= n; v++) if (cand[v]) { res = v; break; }
        answer(res);
    }

    return 0;
}