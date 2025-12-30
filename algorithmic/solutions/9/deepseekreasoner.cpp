#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> p;
vector<pair<int,int>> edges;
map<pair<int,int>, int> edgeIdx;
vector<int> parent, depth, in, out;
vector<vector<int>> children;
int timer;

bool in_subtree(int v, int x) {
    return in[v] <= in[x] && in[x] < out[v];
}

void dfs(int u, int par) {
    parent[u] = par;
    in[u] = timer++;
    for (int v : children[u]) {
        if (v == par) continue;
        depth[v] = depth[u] + 1;
        dfs(v, u);
    }
    out[u] = timer;
}

vector<int> get_upward_matching() {
    vector<pair<int,int>> cand;
    for (int v = 2; v <= n; ++v) {
        int u = parent[v];
        if (u == 0) continue;
        if (!in_subtree(v, p[v])) {
            cand.emplace_back(u, v);
        }
    }
    sort(cand.begin(), cand.end(), [](const pair<int,int>& a, const pair<int,int>& b) {
        return depth[a.second] > depth[b.second];
    });
    vector<bool> used(n+1, false);
    vector<int> matching;
    for (auto& e : cand) {
        int u = e.first, v = e.second;
        if (!used[u] && !used[v]) {
            used[u] = used[v] = true;
            matching.push_back(edgeIdx[{u, v}]);
        }
    }
    return matching;
}

vector<int> get_downward_matching() {
    vector<pair<int,int>> cand;
    for (int v = 2; v <= n; ++v) {
        int u = parent[v];
        if (u == 0) continue;
        if (in_subtree(v, p[u])) {
            cand.emplace_back(u, v);
        }
    }
    sort(cand.begin(), cand.end(), [](const pair<int,int>& a, const pair<int,int>& b) {
        return depth[a.second] > depth[b.second];
    });
    vector<bool> used(n+1, false);
    vector<int> matching;
    for (auto& e : cand) {
        int u = e.first, v = e.second;
        if (!used[u] && !used[v]) {
            used[u] = used[v] = true;
            matching.push_back(edgeIdx[{u, v}]);
        }
    }
    return matching;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    while (T--) {
        cin >> n;
        p.resize(n+1);
        for (int i = 1; i <= n; ++i) cin >> p[i];
        edges.resize(n);
        edgeIdx.clear();
        vector<vector<int>> adj(n+1);
        for (int i = 1; i < n; ++i) {
            int u, v;
            cin >> u >> v;
            edges[i] = {u, v};
            edgeIdx[{u, v}] = i;
            edgeIdx[{v, u}] = i;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // prepare rooted tree
        parent.assign(n+1, 0);
        depth.assign(n+1, 0);
        in.assign(n+1, 0);
        out.assign(n+1, 0);
        children = adj; // temporary, will be refined
        // rebuild children lists (excluding parent)
        for (int i = 1; i <= n; ++i) children[i].clear();
        timer = 0;
        function<void(int,int)> dfs2 = [&](int u, int par) {
            parent[u] = par;
            in[u] = timer++;
            for (int v : adj[u]) {
                if (v == par) continue;
                depth[v] = depth[u] + 1;
                children[u].push_back(v);
                dfs2(v, u);
            }
            out[u] = timer;
        };
        dfs2(1, 0);

        vector<vector<int>> operations;
        bool up_next = true;
        while (true) {
            bool sorted = true;
            for (int i = 1; i <= n; ++i)
                if (p[i] != i) { sorted = false; break; }
            if (sorted) break;

            vector<int> matching;
            if (up_next) matching = get_upward_matching();
            else         matching = get_downward_matching();

            if (matching.empty()) {
                up_next = !up_next;   // try the other phase
                continue;
            }

            for (int idx : matching) {
                auto [u, v] = edges[idx];
                swap(p[u], p[v]);
            }
            operations.push_back(matching);
            up_next = !up_next;
        }

        cout << operations.size() << "\n";
        for (auto& op : operations) {
            cout << op.size();
            for (int idx : op) cout << " " << idx;
            cout << "\n";
        }
    }
    return 0;
}