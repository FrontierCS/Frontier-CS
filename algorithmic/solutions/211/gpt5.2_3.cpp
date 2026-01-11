#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long id;
    long long x, y;
    int type; // 0=R, 1=S, 2=C
};

struct Edge {
    int u, v;
    long long w;
    bool active;
};

static const long long INF = (long long)4e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    int V = N + K;

    vector<Node> nodes(V);
    for (int i = 0; i < V; i++) {
        long long id, x, y;
        char t;
        cin >> id >> x >> y >> t;
        int tp = 2;
        if (t == 'R') tp = 0;
        else if (t == 'S') tp = 1;
        else tp = 2;
        nodes[i] = {id, x, y, tp};
    }

    auto weight = [&](int i, int j) -> long long {
        int ti = nodes[i].type, tj = nodes[j].type;
        if (ti == 2 && tj == 2) return INF; // C-C forbidden
        long long dx = nodes[i].x - nodes[j].x;
        long long dy = nodes[i].y - nodes[j].y;
        long long D = dx * dx + dy * dy;
        if (ti == 2 || tj == 2) return 5LL * D;            // C-any robot
        if (ti == 0 && tj == 0) return 5LL * D;            // R-R
        return 4LL * D;                                     // at least one S
    };

    auto primMST = [&](const vector<int>& verts, bool &connected) -> vector<Edge> {
        int m = (int)verts.size();
        vector<long long> dist(m, INF);
        vector<int> parent(m, -1);
        vector<char> used(m, 0);
        dist[0] = 0;

        vector<Edge> mst;
        mst.reserve(max(0, m - 1));

        int usedCnt = 0;
        for (int it = 0; it < m; it++) {
            int u = -1;
            long long best = INF;
            for (int i = 0; i < m; i++) {
                if (!used[i] && dist[i] < best) {
                    best = dist[i];
                    u = i;
                }
            }
            if (u == -1 || best >= INF/2) break;
            used[u] = 1;
            usedCnt++;

            if (parent[u] != -1) {
                int gu = verts[u];
                int gp = verts[parent[u]];
                mst.push_back({gu, gp, dist[u], true});
            }

            int gu = verts[u];
            for (int v = 0; v < m; v++) {
                if (used[v]) continue;
                int gv = verts[v];
                long long wuv = weight(gu, gv);
                if (wuv < dist[v]) {
                    dist[v] = wuv;
                    parent[v] = u;
                }
            }
        }

        connected = (usedCnt == m);
        return mst;
    };

    vector<int> allVerts(V);
    iota(allVerts.begin(), allVerts.end(), 0);

    bool connectedAll = false;
    vector<Edge> mstEdges = primMST(allVerts, connectedAll);

    // Fallback: if somehow disconnected, connect robots only (ignore relays).
    if (!connectedAll) {
        vector<int> robotVerts;
        robotVerts.reserve(V);
        for (int i = 0; i < V; i++) if (nodes[i].type != 2) robotVerts.push_back(i);
        if (robotVerts.empty()) {
            cout << "#\n#\n";
            return 0;
        }
        bool connectedRobots = false;
        vector<Edge> robotMST = primMST(robotVerts, connectedRobots);
        // Output
        cout << "#\n";
        vector<pair<long long,long long>> outE;
        outE.reserve(robotMST.size());
        for (auto &e : robotMST) {
            long long a = nodes[e.u].id, b = nodes[e.v].id;
            if (a > b) swap(a,b);
            outE.push_back({a,b});
        }
        sort(outE.begin(), outE.end());
        outE.erase(unique(outE.begin(), outE.end()), outE.end());
        if (outE.empty()) {
            cout << "#\n";
        } else {
            for (size_t i = 0; i < outE.size(); i++) {
                if (i) cout << "#";
                cout << outE[i].first << "-" << outE[i].second;
            }
            cout << "\n";
        }
        return 0;
    }

    vector<Edge> edges;
    edges.reserve(mstEdges.size() + 4096);
    for (auto &e : mstEdges) edges.push_back(e);

    vector<vector<int>> adj(V);
    vector<int> deg(V, 0);
    for (int idx = 0; idx < (int)edges.size(); idx++) {
        adj[edges[idx].u].push_back(idx);
        adj[edges[idx].v].push_back(idx);
        deg[edges[idx].u]++;
        deg[edges[idx].v]++;
    }

    vector<char> removed(V, 0); // only relays will be removed

    auto deactivateEdge = [&](int ei) {
        if (!edges[ei].active) return;
        edges[ei].active = false;
        deg[edges[ei].u]--;
        deg[edges[ei].v]--;
    };

    // Prune leaf relays
    queue<int> q;
    for (int i = 0; i < V; i++) {
        if (nodes[i].type == 2 && deg[i] <= 1) q.push(i);
    }
    while (!q.empty()) {
        int r = q.front(); q.pop();
        if (removed[r]) continue;
        if (nodes[r].type != 2) continue;
        if (deg[r] == 0) {
            removed[r] = 1;
            continue;
        }
        if (deg[r] > 1) continue;
        int eidx = -1;
        int nb = -1;
        for (int ei : adj[r]) {
            if (!edges[ei].active) continue;
            eidx = ei;
            nb = (edges[ei].u == r) ? edges[ei].v : edges[ei].u;
            break;
        }
        if (eidx == -1) {
            removed[r] = 1;
            deg[r] = 0;
            continue;
        }
        deactivateEdge(eidx);
        removed[r] = 1;

        // neighbor cannot be a relay due to forbidden C-C, but keep safety
        if (!removed[nb] && nodes[nb].type == 2 && deg[nb] <= 1) q.push(nb);
    }

    auto neighborMST = [&](const vector<int>& neigh, long long &mstCost) -> vector<pair<int,int>> {
        int d = (int)neigh.size();
        vector<pair<int,int>> chosen;
        mstCost = 0;
        if (d <= 1) return chosen;
        if (d == 2) {
            mstCost = weight(neigh[0], neigh[1]);
            chosen.push_back({neigh[0], neigh[1]});
            return chosen;
        }
        vector<long long> dist(d, INF);
        vector<int> parent(d, -1);
        vector<char> used(d, 0);
        dist[0] = 0;

        for (int it = 0; it < d; it++) {
            int u = -1;
            long long best = INF;
            for (int i = 0; i < d; i++) {
                if (!used[i] && dist[i] < best) {
                    best = dist[i];
                    u = i;
                }
            }
            if (u == -1) break;
            used[u] = 1;
            mstCost += dist[u];
            if (parent[u] != -1) {
                chosen.push_back({neigh[u], neigh[parent[u]]});
            }
            int gu = neigh[u];
            for (int v = 0; v < d; v++) {
                if (used[v]) continue;
                int gv = neigh[v];
                long long wuv = weight(gu, gv);
                if (wuv < dist[v]) {
                    dist[v] = wuv;
                    parent[v] = u;
                }
            }
        }
        return chosen;
    };

    // Try removing remaining relays if cheaper/equal to reconnect neighbors directly with robot edges
    for (int r = 0; r < V; r++) {
        if (nodes[r].type != 2 || removed[r] || deg[r] < 2) continue;

        vector<int> neigh;
        neigh.reserve(deg[r]);
        long long starCost = 0;
        for (int ei : adj[r]) {
            if (!edges[ei].active) continue;
            int nb = (edges[ei].u == r) ? edges[ei].v : edges[ei].u;
            neigh.push_back(nb);
            starCost += edges[ei].w;
        }
        int d = (int)neigh.size();
        if (d < 2) continue;

        long long mstCost = 0;
        vector<pair<int,int>> addEdges = neighborMST(neigh, mstCost);

        if (mstCost <= starCost) {
            // remove relay r
            for (int ei : adj[r]) {
                if (!edges[ei].active) continue;
                deactivateEdge(ei);
            }
            removed[r] = 1;

            // add MST edges among neighbor robots
            for (auto [a, b] : addEdges) {
                long long ww = weight(a, b);
                int idx = (int)edges.size();
                edges.push_back({a, b, ww, true});
                adj[a].push_back(idx);
                adj[b].push_back(idx);
                deg[a]++;
                deg[b]++;
            }
        }
    }

    vector<long long> relayIds;
    relayIds.reserve(K);
    for (int i = 0; i < V; i++) {
        if (nodes[i].type == 2 && !removed[i] && deg[i] > 0) relayIds.push_back(nodes[i].id);
    }
    sort(relayIds.begin(), relayIds.end());
    relayIds.erase(unique(relayIds.begin(), relayIds.end()), relayIds.end());

    if (relayIds.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < relayIds.size(); i++) {
            if (i) cout << "#";
            cout << relayIds[i];
        }
        cout << "\n";
    }

    vector<pair<long long,long long>> outEdges;
    outEdges.reserve(V);
    for (auto &e : edges) {
        if (!e.active) continue;
        // Ensure no C-C edges (safety)
        if (nodes[e.u].type == 2 && nodes[e.v].type == 2) continue;
        long long a = nodes[e.u].id, b = nodes[e.v].id;
        if (a > b) swap(a, b);
        outEdges.push_back({a, b});
    }
    sort(outEdges.begin(), outEdges.end());
    outEdges.erase(unique(outEdges.begin(), outEdges.end()), outEdges.end());

    if (outEdges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < outEdges.size(); i++) {
            if (i) cout << "#";
            cout << outEdges[i].first << "-" << outEdges[i].second;
        }
        cout << "\n";
    }

    return 0;
}