#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long id;
    int x, y;
    char t; // 'R', 'S', 'C'
    bool isRobot() const { return t != 'C'; }
    bool isS() const { return t == 'S'; }
    bool isC() const { return t == 'C'; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    int M = N + K;
    vector<Node> nodes(M);
    for (int i = 0; i < M; ++i) {
        long long id; int x, y; char t;
        cin >> id >> x >> y >> t;
        nodes[i] = {id, x, y, t};
    }
    
    auto weight = [&](int i, int j) -> double {
        if (nodes[i].isC() && nodes[j].isC()) return 1e300; // disallowed
        long long dx = (long long)nodes[i].x - nodes[j].x;
        long long dy = (long long)nodes[i].y - nodes[j].y;
        long long d2 = dx*dx + dy*dy;
        double factor = 1.0;
        if (!nodes[i].isC() && !nodes[j].isC()) {
            if (nodes[i].isS() || nodes[j].isS()) factor = 0.8;
            else factor = 1.0;
        } else {
            factor = 1.0; // C to any robot
        }
        return factor * (double)d2;
    };
    
    // Prim's algorithm O(M^2) to build MST over all nodes with C-C edges forbidden
    const double INF = 1e300;
    vector<double> dist(M, INF);
    vector<int> parent(M, -1);
    vector<char> in(M, 0);
    
    int start = -1;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].isRobot()) { start = i; break; }
    }
    if (start == -1) start = 0; // should not happen as N >= 1
    dist[start] = 0.0;
    
    vector<pair<int,int>> mstEdges;
    mstEdges.reserve(M-1);
    
    for (int it = 0; it < M; ++it) {
        int u = -1;
        double best = INF;
        for (int i = 0; i < M; ++i) {
            if (!in[i] && dist[i] < best) {
                best = dist[i];
                u = i;
            }
        }
        if (u == -1) break; // disconnected shouldn't happen
        in[u] = 1;
        if (parent[u] != -1) {
            mstEdges.emplace_back(parent[u], u);
        }
        for (int v = 0; v < M; ++v) {
            if (in[v]) continue;
            double w = weight(u, v);
            if (w < dist[v]) {
                dist[v] = w;
                parent[v] = u;
            }
        }
    }
    
    // Build adjacency from MST
    vector<vector<int>> adj(M);
    adj.assign(M, {});
    for (auto &e : mstEdges) {
        int u = e.first, v = e.second;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    auto removeEdge = [&](int u, int v) {
        auto &au = adj[u];
        for (size_t i = 0; i < au.size(); ++i) {
            if (au[i] == v) {
                au[i] = au.back();
                au.pop_back();
                break;
            }
        }
        auto &av = adj[v];
        for (size_t i = 0; i < av.size(); ++i) {
            if (av[i] == u) {
                av[i] = av.back();
                av.pop_back();
                break;
            }
        }
    };
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    
    vector<char> removed(M, 0);
    // Prune leaf Cs
    for (int i = 0; i < M; ++i) {
        if (nodes[i].isC() && adj[i].size() == 1) {
            int r = adj[i][0];
            removeEdge(i, r);
            removed[i] = 1;
        }
    }
    // Replace degree-2 Cs by direct robot-robot edge if beneficial
    for (int i = 0; i < M; ++i) {
        if (removed[i]) continue;
        if (nodes[i].isC() && adj[i].size() == 2) {
            int u = adj[i][0];
            int v = adj[i][1];
            // Both u and v are robots (since C-C forbidden in MST)
            double curr = weight(u, i) + weight(i, v);
            double alt = weight(u, v);
            if (alt <= curr) {
                removeEdge(i, u);
                removeEdge(i, v);
                removed[i] = 1;
                addEdge(u, v);
            }
        }
    }
    
    // Collect selected relay stations (Cs with degree > 0)
    vector<long long> selectedC;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].isC() && !removed[i] && !adj[i].empty()) {
            selectedC.push_back(nodes[i].id);
        }
    }
    sort(selectedC.begin(), selectedC.end());
    
    // Collect final edges
    vector<pair<long long,long long>> finalEdges;
    for (int i = 0; i < M; ++i) {
        if (removed[i]) continue;
        for (int v : adj[i]) {
            if (removed[v]) continue;
            if (i < v) {
                finalEdges.emplace_back(nodes[i].id, nodes[v].id);
            }
        }
    }
    
    // Output
    if (selectedC.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selectedC.size(); ++i) {
            if (i) cout << "#";
            cout << selectedC[i];
        }
        cout << "\n";
    }
    if (finalEdges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < finalEdges.size(); ++i) {
            if (i) cout << "#";
            cout << finalEdges[i].first << "-" << finalEdges[i].second;
        }
        cout << "\n";
    }
    return 0;
}