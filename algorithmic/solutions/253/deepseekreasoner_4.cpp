#include <bits/stdc++.h>
using namespace std;

const int MAX_TRIALS = 30; // number of trials per test
const double LOG3 = 1.585; // log2(3)

int t, n, m;
vector<pair<int,int>> edges;
vector<bool> blocked; // true if blocked
vector<bool> repaired;

// DSU
vector<int> parent, rnk;

int find(int x) {
    while (parent[x] != x) {
        parent[x] = parent[parent[x]];
        x = parent[x];
    }
    return x;
}

void union_sets(int a, int b) {
    a = find(a); b = find(b);
    if (a != b) {
        if (rnk[a] < rnk[b]) swap(a, b);
        parent[b] = a;
        if (rnk[a] == rnk[b]) rnk[a]++;
    }
}

// interaction helpers
void block(int x) {
    if (!blocked[x]) {
        cout << "- " << x << endl;
        blocked[x] = true;
    }
}

void unblock(int x) {
    if (blocked[x]) {
        cout << "+ " << x << endl;
        blocked[x] = false;
    }
}

int query(int k, const vector<int>& ys) {
    cout << "? " << k;
    for (int y : ys) cout << " " << y;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// test an edge connecting two different components during forest building
bool test_forest_edge(int idx, int u, int v) {
    unblock(idx);
    bool all_one = true;
    for (int trial = 0; trial < MAX_TRIALS; ++trial) {
        int ans = query(2, {u, v});
        if (ans == 0) {
            all_one = false;
            break;
        }
    }
    if (all_one) {
        // edge is repaired, leave it unblocked
        return true;
    } else {
        block(idx);
        return false;
    }
}

// test a non-forest edge (both ends in same component)
bool test_non_forest_edge(int idx, int f_idx, int u, int v) {
    unblock(idx);
    block(f_idx);
    bool all_one = true;
    for (int trial = 0; trial < MAX_TRIALS; ++trial) {
        int ans = query(2, {u, v});
        if (ans == 0) {
            all_one = false;
            break;
        }
    }
    // restore
    block(idx);
    unblock(f_idx);
    return all_one;
}

void solve_test() {
    cin >> n >> m;
    edges.resize(m+1);
    for (int i = 1; i <= m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    // initialise
    blocked.assign(m+1, false);
    repaired.assign(m+1, false);
    parent.resize(n+1);
    iota(parent.begin(), parent.end(), 0);
    rnk.assign(n+1, 0);

    // block all edges
    for (int i = 1; i <= m; ++i) {
        block(i);
    }

    // forest adjacency (for the final tree)
    vector<vector<pair<int,int>>> forest_adj(n+1);
    int forest_edges = 0;

    // random order for edge processing
    vector<int> order(m);
    iota(order.begin(), order.end(), 1);
    random_shuffle(order.begin(), order.end());

    // build spanning forest
    for (int idx : order) {
        if (forest_edges == n-1) break;
        int u = edges[idx].first, v = edges[idx].second;
        if (find(u) == find(v)) continue; // same component -> will test later
        if (test_forest_edge(idx, u, v)) {
            repaired[idx] = true;
            union_sets(u, v);
            forest_adj[u].push_back({v, idx});
            forest_adj[v].push_back({u, idx});
            forest_edges++;
        }
    }

    // now the forest is a single tree (connected). compute parent and depth.
    vector<int> par(n+1, -1), depth(n+1), edge_to_par(n+1, -1);
    queue<int> q;
    q.push(1);
    par[1] = 0;
    depth[1] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (auto &p : forest_adj[u]) {
            int v = p.first, eidx = p.second;
            if (v == par[u]) continue;
            par[v] = u;
            edge_to_par[v] = eidx;
            depth[v] = depth[u] + 1;
            q.push(v);
        }
    }

    // test all remaining edges
    for (int idx = 1; idx <= m; ++idx) {
        if (repaired[idx]) continue;
        int u = edges[idx].first, v = edges[idx].second;
        // find a forest edge on the path between u and v
        int a = u, b = v;
        while (depth[a] > depth[b]) a = par[a];
        while (depth[b] > depth[a]) b = par[b];
        while (a != b) {
            a = par[a];
            b = par[b];
        }
        int lca = a;
        int f_edge = -1;
        if (u != lca) {
            f_edge = edge_to_par[u];
        } else {
            f_edge = edge_to_par[v];
        }
        // test
        bool res = test_non_forest_edge(idx, f_edge, u, v);
        repaired[idx] = res;
    }

    // output answer
    cout << "!";
    for (int i = 1; i <= m; ++i) {
        cout << " " << repaired[i];
    }
    cout << endl;
    int verdict;
    cin >> verdict;
    if (verdict != 1) exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> t;
    srand(time(0));
    while (t--) {
        solve_test();
    }
    return 0;
}