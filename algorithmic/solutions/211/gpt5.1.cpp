#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char type;
};

struct Edge {
    int u, v;
    long long w; // weight * 5 (so 5*D for factor 1, 4*D for factor 0.8)
};

struct DSU {
    vector<int> parent, rnk;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        parent.resize(n);
        rnk.assign(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }
    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        if (rnk[a] < rnk[b]) swap(a, b);
        parent[b] = a;
        if (rnk[a] == rnk[b]) ++rnk[a];
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    int total = N + K;

    vector<Node> nodes(total);
    for (int i = 0; i < total; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
    }

    // Identify robots (R or S) vs relay stations (C)
    vector<int> robotIndices;
    robotIndices.reserve(N);
    for (int i = 0; i < total; ++i) {
        if (nodes[i].type != 'C') {
            robotIndices.push_back(i);
        }
    }
    int nRob = (int)robotIndices.size();

    vector<int> idxRobotOf(total, -1);
    for (int i = 0; i < nRob; ++i) {
        idxRobotOf[robotIndices[i]] = i;
    }

    long long approxEdgesAll = 1LL * total * (total - 1) / 2 - 1LL * K * (K - 1) / 2;
    long long approxEdgesRob = 1LL * nRob * (nRob - 1) / 2;

    vector<Edge> edgesAll;
    vector<Edge> edgesRob;
    edgesAll.reserve((size_t)max(0LL, approxEdgesAll));
    edgesRob.reserve((size_t)max(0LL, approxEdgesRob));

    // Build all possible valid edges
    for (int i = 0; i < total; ++i) {
        bool isCi = (nodes[i].type == 'C');
        for (int j = i + 1; j < total; ++j) {
            bool isCj = (nodes[j].type == 'C');
            if (isCi && isCj) continue; // C-C not allowed

            long long dx = (long long)nodes[i].x - nodes[j].x;
            long long dy = (long long)nodes[i].y - nodes[j].y;
            long long D = dx * dx + dy * dy;

            long long w;
            if (!isCi && !isCj && (nodes[i].type == 'S' || nodes[j].type == 'S')) {
                // S-S or R-S: factor 0.8 -> 4*D, but we store 5*cost, so 5*0.8*D = 4*D
                w = 4 * D;
            } else {
                // R-R or any with C: factor 1.0 -> 5*D
                w = 5 * D;
            }

            edgesAll.push_back({i, j, w});
            if (!isCi && !isCj) { // both are robots (R or S)
                int ri = idxRobotOf[i];
                int rj = idxRobotOf[j];
                edgesRob.push_back({ri, rj, w});
            }
        }
    }

    auto cmpEdge = [](const Edge &a, const Edge &b) {
        return a.w < b.w;
    };

    // MST on robots only (baseline)
    vector<Edge> mstRobEdges;
    mstRobEdges.reserve(max(0, nRob - 1));
    long long costRob5 = 0;
    if (nRob > 1) {
        sort(edgesRob.begin(), edgesRob.end(), cmpEdge);
        DSU dsuRob(nRob);
        int used = 0;
        for (const auto &e : edgesRob) {
            if (dsuRob.unite(e.u, e.v)) {
                mstRobEdges.push_back(e);
                costRob5 += e.w;
                if (++used == nRob - 1) break;
            }
        }
    }

    // MST on all nodes (robots + Cs), then prune leaf Cs
    sort(edgesAll.begin(), edgesAll.end(), cmpEdge);
    DSU dsuAll(total);
    vector<Edge> mstAllEdges;
    mstAllEdges.reserve(max(0, total - 1));
    for (const auto &e : edgesAll) {
        if (dsuAll.unite(e.u, e.v)) {
            mstAllEdges.push_back(e);
            if ((int)mstAllEdges.size() == total - 1) break;
        }
    }

    vector<vector<pair<int,int>>> adj(total); // neighbor, edgeIndex
    int mstEdgeCount = (int)mstAllEdges.size();
    vector<char> edgeAlive(mstEdgeCount, 1);

    for (int i = 0; i < mstEdgeCount; ++i) {
        int u = mstAllEdges[i].u;
        int v = mstAllEdges[i].v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    vector<int> deg(total);
    vector<char> removed(total, 0);
    for (int i = 0; i < total; ++i) {
        deg[i] = (int)adj[i].size();
    }

    queue<int> q;
    for (int i = 0; i < total; ++i) {
        if (nodes[i].type == 'C' && deg[i] == 1) {
            q.push(i);
        }
    }

    while (!q.empty()) {
        int v = q.front();
        q.pop();
        if (removed[v]) continue;
        if (nodes[v].type != 'C') continue;
        if (deg[v] != 1) continue;

        removed[v] = 1;
        for (auto &pr : adj[v]) {
            int u = pr.first;
            int ei = pr.second;
            if (!edgeAlive[ei]) continue;
            edgeAlive[ei] = 0;
            deg[v]--;
            deg[u]--;
            if (nodes[u].type == 'C' && !removed[u] && deg[u] == 1) {
                q.push(u);
            }
            break;
        }
    }

    vector<Edge> steinerEdges;
    steinerEdges.reserve(mstEdgeCount);
    long long costSteiner5 = 0;
    for (int i = 0; i < mstEdgeCount; ++i) {
        if (edgeAlive[i]) {
            steinerEdges.push_back(mstAllEdges[i]);
            costSteiner5 += mstAllEdges[i].w;
        }
    }

    vector<int> selectedRelayIndices;
    for (int i = 0; i < total; ++i) {
        if (nodes[i].type == 'C' && !removed[i] && deg[i] > 0) {
            selectedRelayIndices.push_back(i);
        }
    }

    // Choose better network: Steiner vs robots-only
    bool useSteiner = false;
    if (costSteiner5 < costRob5) {
        useSteiner = true;
    }

    if (useSteiner) {
        // Output selected relay stations
        if (selectedRelayIndices.empty()) {
            cout << "#\n";
        } else {
            for (size_t i = 0; i < selectedRelayIndices.size(); ++i) {
                if (i) cout << '#';
                cout << nodes[selectedRelayIndices[i]].id;
            }
            cout << '\n';
        }
        // Output communication links
        if (steinerEdges.empty()) {
            cout << "#\n";
        } else {
            for (size_t i = 0; i < steinerEdges.size(); ++i) {
                if (i) cout << '#';
                cout << nodes[steinerEdges[i].u].id << '-' << nodes[steinerEdges[i].v].id;
            }
            cout << '\n';
        }
    } else {
        // Use robots-only MST (no relays)
        cout << "#\n";
        if (mstRobEdges.empty()) {
            cout << "#\n";
        } else {
            for (size_t i = 0; i < mstRobEdges.size(); ++i) {
                if (i) cout << '#';
                int uNode = robotIndices[mstRobEdges[i].u];
                int vNode = robotIndices[mstRobEdges[i].v];
                cout << nodes[uNode].id << '-' << nodes[vNode].id;
            }
            cout << '\n';
        }
    }

    return 0;
}