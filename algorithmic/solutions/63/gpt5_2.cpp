#include <bits/stdc++.h>
using namespace std;

struct Graph {
    int n, m;
    vector<int> U, V;
    vector<vector<pair<int,int>>> adj;
    void read() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        cout.tie(nullptr);
        cin >> n >> m;
        U.resize(m);
        V.resize(m);
        adj.assign(n, {});
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            U[i] = u;
            V[i] = v;
            adj[u].push_back({v, i});
            adj[v].push_back({u, i});
        }
    }
};

struct DFSTree {
    int n, m, root;
    vector<int> parent, depth, tin, tout, parentEdge, order;
    vector<char> isTreeEdge;
    vector<int> treeParent, treeChild;
    inline bool isAncestor(int a, int b) const {
        return tin[a] <= tin[b] && tout[b] <= tout[a];
    }
};

static inline int orientEdge(const Graph &g, int ei, int from, int to) {
    // return bit for edge ei: 0 means U->V, 1 means V->U
    if (g.U[ei] == from && g.V[ei] == to) return 0;
    if (g.U[ei] == to && g.V[ei] == from) return 1;
    // Should not happen
    return 0;
}

DFSTree buildDFS(const Graph &g, int root, mt19937 &rng) {
    int n = g.n, m = g.m;
    vector<vector<pair<int,int>>> adj = g.adj; // copy to shuffle
    for (int i = 0; i < n; ++i) {
        shuffle(adj[i].begin(), adj[i].end(), rng);
    }
    DFSTree T;
    T.n = n; T.m = m; T.root = root;
    T.parent.assign(n, -1);
    T.depth.assign(n, 0);
    T.tin.assign(n, -1);
    T.tout.assign(n, -1);
    T.parentEdge.assign(n, -1);
    T.isTreeEdge.assign(m, 0);
    T.treeParent.assign(m, -1);
    T.treeChild.assign(m, -1);
    vector<char> vis(n, 0);
    vector<int> idx(n, 0);
    vector<int> st;
    st.reserve(n);
    int timer = 0;
    // DFS from root
    st.push_back(root);
    vis[root] = 1;
    T.tin[root] = timer++;
    T.order.clear();
    T.order.reserve(n);
    T.order.push_back(root);
    while (!st.empty()) {
        int v = st.back();
        if (idx[v] < (int)adj[v].size()) {
            auto [to, ei] = adj[v][idx[v]++];
            if (!vis[to]) {
                vis[to] = 1;
                T.parent[to] = v;
                T.parentEdge[to] = ei;
                T.depth[to] = T.depth[v] + 1;
                T.tin[to] = timer++;
                T.order.push_back(to);
                T.isTreeEdge[ei] = 1;
                T.treeParent[ei] = v;
                T.treeChild[ei] = to;
                st.push_back(to);
            }
        } else {
            st.pop_back();
            T.tout[v] = timer++;
        }
    }
    // In case graph is not connected due to some issue (shouldn't happen), cover remaining
    for (int v = 0; v < n; ++v) if (!vis[v]) {
        st.push_back(v);
        vis[v] = 1;
        T.parent[v] = -1;
        T.depth[v] = 0;
        T.tin[v] = timer++;
        T.order.push_back(v);
        while (!st.empty()) {
            int x = st.back();
            if (idx[x] < (int)adj[x].size()) {
                auto [to, ei] = adj[x][idx[x]++];
                if (!vis[to]) {
                    vis[to] = 1;
                    T.parent[to] = x;
                    T.parentEdge[to] = ei;
                    T.depth[to] = T.depth[x] + 1;
                    T.tin[to] = timer++;
                    T.order.push_back(to);
                    T.isTreeEdge[ei] = 1;
                    T.treeParent[ei] = x;
                    T.treeChild[ei] = to;
                    st.push_back(to);
                }
            } else {
                st.pop_back();
                T.tout[x] = timer++;
            }
        }
    }
    return T;
}

vector<int> buildBits_AllUp(const Graph &g, const DFSTree &T) {
    vector<int> bits(g.m);
    for (int i = 0; i < g.m; ++i) {
        if (T.isTreeEdge[i]) {
            int p = T.treeParent[i], c = T.treeChild[i];
            bits[i] = orientEdge(g, i, c, p); // child -> parent (upward)
        } else {
            int u = g.U[i], v = g.V[i];
            if (T.isAncestor(u, v)) {
                // u ancestor of v => v (desc) -> u (anc)
                bits[i] = orientEdge(g, i, v, u);
            } else {
                // v ancestor of u => u (desc) -> v (anc)
                bits[i] = orientEdge(g, i, u, v);
            }
        }
    }
    return bits;
}

// For B-membership with anc=0: tree edges inside prefix go downward (parent->child), others upward; non-tree edges upward.
vector<int> buildBits_B_membership(const Graph &g, const DFSTree &T, int mid) {
    vector<int> bits(g.m);
    for (int i = 0; i < g.m; ++i) {
        if (T.isTreeEdge[i]) {
            int p = T.treeParent[i], c = T.treeChild[i];
            if (T.tin[c] <= mid) {
                bits[i] = orientEdge(g, i, p, c); // downward on included edges
            } else {
                bits[i] = orientEdge(g, i, c, p); // upward otherwise
            }
        } else {
            int u = g.U[i], v = g.V[i];
            if (T.isAncestor(u, v)) {
                bits[i] = orientEdge(g, i, v, u); // upward: desc -> anc
            } else {
                bits[i] = orientEdge(g, i, u, v);
            }
        }
    }
    return bits;
}

// For A-membership relative to T (root is known B): tree edges inside prefix go upward (child->parent), others downward; non-tree edges downward.
vector<int> buildBits_A_membership(const Graph &g, const DFSTree &T, int mid) {
    vector<int> bits(g.m);
    for (int i = 0; i < g.m; ++i) {
        if (T.isTreeEdge[i]) {
            int p = T.treeParent[i], c = T.treeChild[i];
            if (T.tin[c] <= mid) {
                bits[i] = orientEdge(g, i, c, p); // upward inside S
            } else {
                bits[i] = orientEdge(g, i, p, c); // downward otherwise
            }
        } else {
            int u = g.U[i], v = g.V[i];
            if (T.isAncestor(u, v)) {
                bits[i] = orientEdge(g, i, u, v); // downward: anc -> desc
            } else {
                bits[i] = orientEdge(g, i, v, u);
            }
        }
    }
    return bits;
}

int ask_query(const vector<int> &bits) {
    cout << "0";
    for (int b : bits) {
        cout << " " << b;
    }
    cout << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) {
        exit(0);
    }
    return x;
}

int main() {
    Graph g;
    g.read();
    random_device rd;
    mt19937 rng(rd());
    // Phase 1: find a DFS tree T where B is NOT an ancestor of A (anc=0 under all-upward orientation)
    DFSTree T_sel;
    bool found = false;
    int triesMax = 200; // reasonably within 600 total query budget
    for (int tries = 0; tries < triesMax; ++tries) {
        int r = uniform_int_distribution<int>(0, g.n - 1)(rng);
        DFSTree T = buildDFS(g, r, rng);
        vector<int> bits = buildBits_AllUp(g, T);
        int anc = ask_query(bits);
        if (anc == 0) {
            T_sel = std::move(T);
            found = true;
            break;
        }
    }
    if (!found) {
        // Fallback: try fixed root but vary neighbor orders
        int r = 0;
        for (int tries = 0; tries < triesMax; ++tries) {
            DFSTree T = buildDFS(g, r, rng);
            vector<int> bits = buildBits_AllUp(g, T);
            int anc = ask_query(bits);
            if (anc == 0) {
                T_sel = std::move(T);
                found = true;
                break;
            }
        }
    }
    if (!found) {
        // As ultimate fallback, just use last built DFS with anc possibly 1 (not ideal).
        // But proceed to attempt; correctness may suffer only in rare scenarios.
        int r = 0;
        T_sel = buildDFS(g, r, rng);
    }
    // Phase 1b: binary search B's pre-order index using membership queries on T_sel
    int lo = 0, hi = g.n - 1;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        vector<int> bits = buildBits_B_membership(g, T_sel, mid);
        int ans = ask_query(bits);
        if (ans == 1) hi = mid;
        else lo = mid + 1;
    }
    int B = T_sel.order[lo];
    // Phase 2: build DFS tree rooted at B and locate A via membership queries
    DFSTree T_B = buildDFS(g, B, rng);
    lo = 0; hi = g.n - 1;
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        vector<int> bits = buildBits_A_membership(g, T_B, mid);
        int ans = ask_query(bits);
        if (ans == 1) hi = mid;
        else lo = mid + 1;
    }
    int A = T_B.order[lo];
    // Output guess
    cout << "1 " << A << " " << B << endl;
    cout.flush();
    return 0;
}