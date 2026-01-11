#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <unordered_set>
#include <climits>

using namespace std;

struct Node {
    int id;
    char type;
    int x, y;
};

long long squared_distance(int x1, int y1, int x2, int y2) {
    long long dx = x1 - x2;
    long long dy = y1 - y2;
    return dx * dx + dy * dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    vector<Node> nodes(N + K);
    for (int i = 0; i < N + K; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
    }

    int V = N + K;
    // cost matrix, scaled by 5 to avoid floating point
    vector<vector<long long>> cost(V, vector<long long>(V, LLONG_MAX));

    for (int i = 0; i < V; ++i) {
        for (int j = i + 1; j < V; ++j) {
            if (nodes[i].type == 'C' && nodes[j].type == 'C') {
                continue;  // forbidden edge
            }
            long long d2 = squared_distance(nodes[i].x, nodes[i].y, nodes[j].x, nodes[j].y);
            if (nodes[i].type == 'C' || nodes[j].type == 'C') {
                // relay with robot: factor 1 -> scaled cost = d2 * 5
                cost[i][j] = cost[j][i] = d2 * 5;
            } else {
                // both robots
                if (nodes[i].type == 'S' || nodes[j].type == 'S') {
                    // at least one high-power robot: factor 0.8 -> scaled cost = d2 * 4
                    cost[i][j] = cost[j][i] = d2 * 4;
                } else {
                    // both ordinary robots: factor 1 -> scaled cost = d2 * 5
                    cost[i][j] = cost[j][i] = d2 * 5;
                }
            }
        }
    }

    // Prim's MST on all nodes (excluding C-C edges)
    vector<bool> inMST(V, false);
    vector<long long> minEdge(V, LLONG_MAX);
    vector<int> parent(V, -1);
    minEdge[0] = 0;

    for (int iter = 0; iter < V; ++iter) {
        int u = -1;
        for (int i = 0; i < V; ++i) {
            if (!inMST[i] && (u == -1 || minEdge[i] < minEdge[u])) {
                u = i;
            }
        }
        inMST[u] = true;
        for (int v = 0; v < V; ++v) {
            if (!inMST[v] && cost[u][v] < minEdge[v]) {
                minEdge[v] = cost[u][v];
                parent[v] = u;
            }
        }
    }

    // Build adjacency list of the MST
    vector<unordered_set<int>> adj(V);
    vector<int> deg(V, 0);
    for (int i = 0; i < V; ++i) {
        if (parent[i] != -1) {
            adj[i].insert(parent[i]);
            adj[parent[i]].insert(i);
            deg[i]++;
            deg[parent[i]]++;
        }
    }

    vector<bool> active(V, true);
    queue<int> leafQ;

    // Initial leaf relay pruning
    for (int i = 0; i < V; ++i) {
        if (active[i] && nodes[i].type == 'C' && deg[i] == 1) {
            leafQ.push(i);
        }
    }
    while (!leafQ.empty()) {
        int u = leafQ.front(); leafQ.pop();
        if (!active[u] || nodes[u].type != 'C' || deg[u] != 1) continue;
        active[u] = false;
        int v = *adj[u].begin();  // only neighbor
        adj[u].erase(v);
        adj[v].erase(u);
        deg[u] = 0;
        deg[v]--;
        if (active[v] && nodes[v].type == 'C' && deg[v] == 1) {
            leafQ.push(v);
        }
    }

    // Improvement: replace beneficial degree-2 relays
    bool improved = true;
    while (improved) {
        improved = false;
        vector<int> candidates;
        for (int i = 0; i < V; ++i) {
            if (active[i] && nodes[i].type == 'C' && deg[i] == 2) {
                candidates.push_back(i);
            }
        }
        for (int c : candidates) {
            if (!active[c] || deg[c] != 2) continue;
            auto it = adj[c].begin();
            int u = *it;
            ++it;
            int v = *it;
            long long cost_uv = cost[u][v];
            long long cost_uc = cost[u][c];
            long long cost_cv = cost[c][v];
            if (cost_uv < cost_uc + cost_cv) {
                // Replace relay c with direct edge u-v
                adj[u].erase(c);
                adj[v].erase(c);
                adj[c].clear();
                adj[u].insert(v);
                adj[v].insert(u);
                deg[u]--; deg[v]--;   // removed connections to c
                deg[u]++; deg[v]++;   // added connection between u and v
                deg[c] = 0;
                active[c] = false;
                improved = true;
            }
        }
        // Prune new leaf relays after improvements
        for (int i = 0; i < V; ++i) {
            if (active[i] && nodes[i].type == 'C' && deg[i] == 1) {
                leafQ.push(i);
            }
        }
        while (!leafQ.empty()) {
            int u = leafQ.front(); leafQ.pop();
            if (!active[u] || nodes[u].type != 'C' || deg[u] != 1) continue;
            active[u] = false;
            int v = *adj[u].begin();
            adj[u].erase(v);
            adj[v].erase(u);
            deg[u] = 0;
            deg[v]--;
            if (active[v] && nodes[v].type == 'C' && deg[v] == 1) {
                leafQ.push(v);
            }
        }
    }

    // Output selected relays
    vector<int> relay_ids;
    for (int i = 0; i < V; ++i) {
        if (active[i] && nodes[i].type == 'C') {
            relay_ids.push_back(nodes[i].id);
        }
    }
    sort(relay_ids.begin(), relay_ids.end());
    if (relay_ids.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < relay_ids.size(); ++i) {
            if (i > 0) cout << "#";
            cout << relay_ids[i];
        }
        cout << "\n";
    }

    // Output edges
    vector<pair<int, int>> edges;
    for (int i = 0; i < V; ++i) {
        if (!active[i]) continue;
        for (int j : adj[i]) {
            if (j > i) {
                edges.emplace_back(nodes[i].id, nodes[j].id);
            }
        }
    }
    sort(edges.begin(), edges.end());
    for (size_t i = 0; i < edges.size(); ++i) {
        if (i > 0) cout << "#";
        cout << edges[i].first << "-" << edges[i].second;
    }
    cout << "\n";

    return 0;
}