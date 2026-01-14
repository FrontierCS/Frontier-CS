#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id, x, y;
    char type;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    cin >> N >> K;
    int total = N + K;
    vector<Node> nodes(total);
    vector<int> robot_idx, relay_idx;
    for (int i = 0; i < total; i++) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
        if (nodes[i].type == 'R' || nodes[i].type == 'S') {
            robot_idx.push_back(i);
        } else {
            relay_idx.push_back(i);
        }
    }
    
    auto get_robot_weight = [&](int u, int v) -> long long {
        long long dx = (long long)nodes[u].x - nodes[v].x;
        long long dy = (long long)nodes[u].y - nodes[v].y;
        long long D = dx * dx + dy * dy;
        bool su = nodes[u].type == 'S';
        bool sv = nodes[v].type == 'S';
        return (su || sv) ? 4LL * D : 5LL * D;
    };
    
    auto get_relay_weight = [&](int u, int rc) -> long long {
        long long dx = (long long)nodes[u].x - nodes[rc].x;
        long long dy = (long long)nodes[u].y - nodes[rc].y;
        long long D = dx * dx + dy * dy;
        return 5LL * D;
    };
    
    // Base MST
    vector<tuple<long long, int, int>> base_edges;
    int NR = robot_idx.size();
    for (int i = 0; i < NR; i++) {
        for (int j = i + 1; j < NR; j++) {
            int u = robot_idx[i], v = robot_idx[j];
            long long w = get_robot_weight(u, v);
            base_edges.emplace_back(w, u, v);
        }
    }
    sort(base_edges.begin(), base_edges.end());
    
    vector<int> parent(total), rnk(total, 0);
    auto find = [&](auto&& self, int x) -> int {
        if (parent[x] != x) parent[x] = self(self, parent[x]);
        return parent[x];
    };
    auto unite = [&](int x, int y) -> bool {
        int px = find(find, x), py = find(find, y);
        if (px == py) return false;
        if (rnk[px] < rnk[py]) {
            parent[px] = py;
        } else {
            parent[py] = px;
            if (rnk[px] == rnk[py]) rnk[px]++;
        }
        return true;
    };
    
    for (int i = 0; i < total; i++) parent[i] = i;
    vector<pair<int, int>> base_mst;
    for (auto [w, u, v] : base_edges) {
        if (unite(u, v)) {
            base_mst.emplace_back(min(u, v), max(u, v));
        }
    }
    
    // Base cost
    double base_cost = 0.0;
    for (auto [u, v] : base_mst) {
        long long dx = (long long)nodes[u].x - nodes[v].x;
        long long dy = (long long)nodes[u].y - nodes[v].y;
        long long D = dx * dx + dy * dy;
        char tu = nodes[u].type, tv = nodes[v].type;
        double f = 1.0;
        if (tu != 'C' && tv != 'C') {
            bool su = tu == 'S', sv = tv == 'S';
            f = (su || sv) ? 0.8 : 1.0;
        }
        base_cost += f * (double)D;
    }
    
    // Full graph edges
    vector<tuple<long long, int, int>> all_edges;
    for (auto e : base_edges) {
        all_edges.push_back(e);
    }
    for (int ri : robot_idx) {
        for (int rci : relay_idx) {
            long long w = get_relay_weight(ri, rci);
            all_edges.emplace_back(w, ri, rci);
        }
    }
    sort(all_edges.begin(), all_edges.end());
    
    // Reset UF
    for (int i = 0; i < total; i++) {
        parent[i] = i;
        rnk[i] = 0;
    }
    vector<pair<int, int>> full_mst;
    for (auto [w, u, v] : all_edges) {
        if (unite(u, v)) {
            full_mst.emplace_back(min(u, v), max(u, v));
        }
    }
    
    // Prune
    vector<vector<int>> adj(total);
    vector<int> deg(total, 0);
    for (auto [u, v] : full_mst) {
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }
    queue<int> leaves_q;
    for (int rc : relay_idx) {
        if (deg[rc] == 1) {
            leaves_q.push(rc);
        }
    }
    vector<bool> active(total, true);
    while (!leaves_q.empty()) {
        int c = leaves_q.front(); leaves_q.pop();
        if (!active[c] || deg[c] != 1) continue;
        active[c] = false;
        int neigh = -1;
        for (int nb : adj[c]) {
            if (active[nb]) {
                neigh = nb;
                break;
            }
        }
        if (neigh == -1) continue;
        auto it = find(adj[neigh].begin(), adj[neigh].end(), c);
        if (it != adj[neigh].end()) {
            adj[neigh].erase(it);
        }
        deg[neigh]--;
        if (nodes[neigh].type == 'C' && active[neigh] && deg[neigh] == 1) {
            leaves_q.push(neigh);
        }
    }
    
    // Final edges
    vector<pair<int, int>> final_edges;
    for (auto [u, v] : full_mst) {
        if (active[u] && active[v]) {
            final_edges.emplace_back(u, v);
        }
    }
    
    // Actual cost
    double actual_cost = 0.0;
    for (auto [u, v] : final_edges) {
        long long dx = (long long)nodes[u].x - nodes[v].x;
        long long dy = (long long)nodes[u].y - nodes[v].y;
        long long D = dx * dx + dy * dy;
        char tu = nodes[u].type, tv = nodes[v].type;
        double f = 1.0;
        if (tu != 'C' && tv != 'C') {
            bool su = tu == 'S', sv = tv == 'S';
            f = (su || sv) ? 0.8 : 1.0;
        }
        actual_cost += f * (double)D;
    }
    
    // Decide
    vector<pair<int, int>> output_edges;
    vector<int> selected;
    if (actual_cost <= base_cost + 1e-9) {
        output_edges = final_edges;
        for (int rc : relay_idx) {
            if (active[rc]) {
                selected.push_back(nodes[rc].id);
            }
        }
    } else {
        output_edges = base_mst;
    }
    sort(selected.begin(), selected.end());
    
    // Output first line
    if (selected.empty()) {
        cout << "#" << endl;
    } else {
        for (size_t i = 0; i < selected.size(); i++) {
            if (i > 0) cout << "#";
            cout << selected[i];
        }
        cout << endl;
    }
    
    // Output edges
    vector<pair<int, int>> id_edges;
    for (auto [ui, vi] : output_edges) {
        int id1 = nodes[ui].id;
        int id2 = nodes[vi].id;
        if (id1 > id2) swap(id1, id2);
        id_edges.emplace_back(id1, id2);
    }
    sort(id_edges.begin(), id_edges.end());
    for (size_t i = 0; i < id_edges.size(); i++) {
        if (i > 0) cout << "#";
        cout << id_edges[i].first << "-" << id_edges[i].second;
    }
    cout << endl;
    
    return 0;
}