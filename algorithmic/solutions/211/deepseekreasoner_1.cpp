#include <iostream>
#include <vector>
#include <queue>
#include <unordered_set>
#include <algorithm>
#include <string>
#include <sstream>
#include <climits>

using namespace std;

typedef long long ll;

const ll INF = 1LL << 60;

struct Node {
    int id;
    int x, y;
    char type;
};

ll cost(const Node& a, const Node& b) {
    if (a.type == 'C' && b.type == 'C') return INF;
    ll dx = a.x - b.x;
    ll dy = a.y - b.y;
    ll d2 = dx * dx + dy * dy;
    if (a.type == 'C' || b.type == 'C') {
        return 5LL * d2;   // factor 1.0 -> 5/5
    } else if (a.type == 'S' || b.type == 'S') {
        return 4LL * d2;   // factor 0.8 -> 4/5
    } else {
        return 5LL * d2;   // factor 1.0 -> 5/5
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    int V = N + K;
    vector<Node> nodes(V);
    vector<int> term_idx;   // indices of robots (terminals)
    vector<int> relay_idx;  // indices of optional relays

    for (int i = 0; i < V; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
        if (nodes[i].type == 'R' || nodes[i].type == 'S') {
            term_idx.push_back(i);
        } else { // 'C'
            relay_idx.push_back(i);
        }
    }

    int n_term = term_idx.size();
    vector<bool> is_term(V, false);
    for (int idx : term_idx) is_term[idx] = true;

    // ---------- 1. MST on terminals only ----------
    vector<bool> in_tree0(n_term, false);
    vector<ll> dist0(n_term, INF);
    vector<int> parent0(n_term, -1);
    int start0 = 0; // index in term_idx
    dist0[start0] = 0;
    ll total_cost0 = 0;
    vector<pair<int, int>> edges0; // store global indices (min, max)

    for (int iter = 0; iter < n_term; ++iter) {
        int u_idx = -1;
        ll min_d = INF;
        for (int i = 0; i < n_term; ++i) {
            if (!in_tree0[i] && dist0[i] < min_d) {
                min_d = dist0[i];
                u_idx = i;
            }
        }
        if (u_idx == -1) break;
        in_tree0[u_idx] = true;
        total_cost0 += min_d;
        int u_global = term_idx[u_idx];
        if (parent0[u_idx] != -1) {
            int p_global = term_idx[parent0[u_idx]];
            edges0.emplace_back(min(p_global, u_global), max(p_global, u_global));
        }
        // update distances from u
        for (int v_idx = 0; v_idx < n_term; ++v_idx) {
            if (!in_tree0[v_idx]) {
                ll c = cost(nodes[u_global], nodes[term_idx[v_idx]]);
                if (c < dist0[v_idx]) {
                    dist0[v_idx] = c;
                    parent0[v_idx] = u_idx;
                }
            }
        }
    }

    // ---------- 2. Prim on all nodes (to connect all terminals) ----------
    vector<bool> in_tree(V, false);
    vector<ll> dist(V, INF);
    vector<int> parent(V, -1);
    int start_global = term_idx[0];
    in_tree[start_global] = true;
    dist[start_global] = 0;
    // initialize distances from start_global
    for (int v = 0; v < V; ++v) {
        if (v == start_global) continue;
        ll c = cost(nodes[start_global], nodes[v]);
        if (c < dist[v]) {
            dist[v] = c;
            parent[v] = start_global;
        }
    }
    int term_count = 1;
    ll total_cost1 = 0;
    vector<pair<int, int>> edges1; // global indices (min, max)

    while (term_count < n_term) {
        int u = -1;
        ll min_d = INF;
        for (int i = 0; i < V; ++i) {
            if (!in_tree[i] && dist[i] < min_d) {
                min_d = dist[i];
                u = i;
            }
        }
        if (u == -1) break; // should not happen
        in_tree[u] = true;
        total_cost1 += min_d;
        edges1.emplace_back(min(parent[u], u), max(parent[u], u));
        if (is_term[u]) term_count++;
        // update distances from u
        for (int v = 0; v < V; ++v) {
            if (!in_tree[v]) {
                ll c = cost(nodes[u], nodes[v]);
                if (c < dist[v]) {
                    dist[v] = c;
                    parent[v] = u;
                }
            }
        }
    }

    // ---------- Prune leaf relays from edges1 ----------
    vector<unordered_set<int>> adj(V);
    for (auto& e : edges1) {
        int a = e.first, b = e.second;
        adj[a].insert(b);
        adj[b].insert(a);
    }
    queue<int> leaf_q;
    for (int i = 0; i < V; ++i) {
        if (nodes[i].type == 'C' && adj[i].size() == 1) {
            leaf_q.push(i);
        }
    }
    while (!leaf_q.empty()) {
        int u = leaf_q.front(); leaf_q.pop();
        if (adj[u].size() != 1 || nodes[u].type != 'C') continue;
        int v = *adj[u].begin();
        adj[u].erase(v);
        adj[v].erase(u);
        if (nodes[v].type == 'C' && adj[v].size() == 1) {
            leaf_q.push(v);
        }
    }
    // collect remaining edges and compute total cost after pruning
    vector<pair<int, int>> edges1_pruned;
    ll total_cost1_pruned = 0;
    for (int i = 0; i < V; ++i) {
        for (int j : adj[i]) {
            if (i < j) {
                edges1_pruned.emplace_back(i, j);
                total_cost1_pruned += cost(nodes[i], nodes[j]);
            }
        }
    }

    // ---------- Choose the better tree ----------
    vector<pair<int, int>> chosen_edges;
    bool use_relays = false;
    if (total_cost0 <= total_cost1_pruned) {
        chosen_edges = edges0;
        use_relays = false;
    } else {
        chosen_edges = edges1_pruned;
        use_relays = true;
    }

    // ---------- Prepare output ----------
    // selected relays
    vector<int> selected_relays;
    if (use_relays) {
        // find all relays that appear in chosen_edges
        vector<bool> used(V, false);
        for (auto& e : chosen_edges) {
            used[e.first] = true;
            used[e.second] = true;
        }
        for (int i = 0; i < V; ++i) {
            if (nodes[i].type == 'C' && used[i]) {
                selected_relays.push_back(nodes[i].id);
            }
        }
        sort(selected_relays.begin(), selected_relays.end());
    }
    // edges as strings
    vector<string> edge_strings;
    for (auto& e : chosen_edges) {
        int id1 = nodes[e.first].id;
        int id2 = nodes[e.second].id;
        if (id1 > id2) swap(id1, id2);
        edge_strings.push_back(to_string(id1) + "-" + to_string(id2));
    }
    sort(edge_strings.begin(), edge_strings.end());

    // output first line
    if (selected_relays.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selected_relays.size(); ++i) {
            if (i > 0) cout << "#";
            cout << selected_relays[i];
        }
        cout << "\n";
    }
    // output second line
    if (edge_strings.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edge_strings.size(); ++i) {
            if (i > 0) cout << "#";
            cout << edge_strings[i];
        }
        cout << "\n";
    }

    return 0;
}