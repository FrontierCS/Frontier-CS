#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, LOG;
    vector<vector<int>> g, children;
    vector<int> depth, tin, tout;
    vector<vector<int>> up;
    int timer;

    void init(int n_) {
        n = n_;
        LOG = 0;
        while ((1 << LOG) <= n) ++LOG;
        g.assign(n + 1, {});
        children.assign(n + 1, {});
        depth.assign(n + 1, 0);
        tin.assign(n + 1, 0);
        tout.assign(n + 1, 0);
        up.assign(LOG, vector<int>(n + 1, 1));
        timer = 0;
    }

    void add_edge(int u, int v) {
        g[u].push_back(v);
        g[v].push_back(u);
    }

    void build_rooted_tree() {
        // iterative DFS to set tin/tout, parent, depth, and children
        vector<tuple<int,int,int>> st;
        st.emplace_back(1, 0, 0);
        up[0][1] = 1;
        depth[1] = 0;
        while (!st.empty()) {
            auto [u, p, state] = st.back();
            st.pop_back();
            if (state == 0) {
                tin[u] = ++timer;
                st.emplace_back(u, p, 1);
                for (int v : g[u]) {
                    if (v == p) continue;
                    up[0][v] = u;
                    depth[v] = depth[u] + 1;
                    children[u].push_back(v);
                    st.emplace_back(v, u, 0);
                }
            } else {
                tout[u] = timer;
            }
        }
        for (int k = 1; k < LOG; ++k) {
            for (int v = 1; v <= n; ++v) {
                up[k][v] = up[k-1][ up[k-1][v] ];
            }
        }
    }

    bool is_ancestor(int u, int v) {
        return tin[u] <= tin[v] && tout[v] <= tout[u];
    }

    int lca(int u, int v) {
        if (is_ancestor(u, v)) return u;
        if (is_ancestor(v, u)) return v;
        for (int k = LOG - 1; k >= 0; --k) {
            int uu = up[k][u];
            if (!is_ancestor(uu, v)) u = uu;
        }
        return up[0][u];
    }

    int choose_best_query(const vector<int>& candList, const vector<char>& inC) {
        // Build arrC and preC using Euler order
        vector<int> arrC(n + 2, 0), preC(n + 2, 0);
        for (int u : candList) arrC[tin[u]]++;
        for (int i = 1; i <= n; ++i) preC[i] = preC[i-1] + arrC[i];

        // For each parent p with at least one child in C, compute L_p = lca of its children in C
        vector<int> freqL(n + 1, 0);
        int parentsWithChildInC = 0;
        bool rootHasChildInC = false;
        int L1 = 0;
        for (int p = 1; p <= n; ++p) {
            int L = 0;
            for (int c : children[p]) {
                if (inC[c]) {
                    if (L == 0) L = c;
                    else L = lca(L, c);
                }
            }
            if (L != 0) {
                parentsWithChildInC++;
                freqL[L]++;
                if (p == 1) {
                    rootHasChildInC = true;
                    L1 = L;
                }
            }
        }

        // Build arrL and preL for fast range sums of freqL over subtrees
        vector<int> arrL(n + 2, 0), preL(n + 2, 0);
        for (int u = 1; u <= n; ++u) {
            if (freqL[u]) arrL[tin[u]] += freqL[u];
        }
        for (int i = 1; i <= n; ++i) preL[i] = preL[i-1] + arrL[i];

        auto subtree_sum = [&](const vector<int>& pref, int x) -> int {
            return pref[tout[x]] - pref[tin[x]-1];
        };

        int bestX = 1;
        int bestVal = INT_MAX;
        for (int x = 1; x <= n; ++x) {
            int inside = subtree_sum(preC, x);
            int ancCount = subtree_sum(preL, x); // number of p with x ancestor of L_p
            int s0_noroot = parentsWithChildInC - ancCount;

            bool rootOutside = (inC[1] && x != 1);
            bool ancL1 = false;
            if (rootHasChildInC) ancL1 = is_ancestor(x, L1);
            int s0 = s0_noroot + ((rootOutside && (!rootHasChildInC || ancL1)) ? 1 : 0);

            int worst = max(inside, s0);
            if (worst < bestVal || (worst == bestVal && depth[x] < depth[bestX])) {
                bestVal = worst;
                bestX = x;
            }
        }
        return bestX;
    }

    void solve_case() {
        build_rooted_tree();

        vector<int> candList;
        candList.reserve(n);
        for (int u = 1; u <= n; ++u) candList.push_back(u);
        vector<char> inC(n + 1, 1);

        int queries = 0;
        while ((int)candList.size() > 1) {
            int x = choose_best_query(candList, inC);

            cout << "? " << x << endl;
            cout.flush();
            int r;
            if (!(cin >> r)) return;
            queries++;
            // Update candidate set
            if (r == 1) {
                vector<int> newList;
                newList.reserve(candList.size());
                for (int u : candList) {
                    if (tin[x] <= tin[u] && tin[u] <= tout[x]) {
                        newList.push_back(u);
                    }
                }
                fill(inC.begin(), inC.end(), 0);
                for (int u : newList) inC[u] = 1;
                candList.swap(newList);
            } else {
                vector<char> present(n + 1, 0);
                vector<int> newList;
                newList.reserve(candList.size());
                for (int u : candList) {
                    if (!(tin[x] <= tin[u] && tin[u] <= tout[x])) {
                        int p = (u == 1 ? 1 : up[0][u]);
                        if (!present[p]) {
                            present[p] = 1;
                            newList.push_back(p);
                        }
                    }
                }
                fill(inC.begin(), inC.end(), 0);
                for (int u : newList) inC[u] = 1;
                candList.swap(newList);
            }
            if (queries > 160) return;
        }

        int ans = candList.empty() ? 1 : candList[0];
        cout << "! " << ans << endl;
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        Solver solver;
        solver.init(n);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            solver.add_edge(u, v);
        }
        solver.solve_case();
    }
    return 0;
}