#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char type; // 'R','S' for robots; 'C' for relay
};

static inline long long dist2(const Node& a, const Node& b) {
    long long dx = (long long)a.x - b.x;
    long long dy = (long long)a.y - b.y;
    return dx * dx + dy * dy;
}

// Scaled by 10 to keep integer:
// R-R: 10*D
// R-S or S-S: 8*D
static inline long long w_robot_robot_scaled(const Node& a, const Node& b) {
    long long d = dist2(a, b);
    int mult = (a.type == 'R' && b.type == 'R') ? 10 : 8;
    return (long long)mult * d;
}

// Relay to any robot: 10*D (since 1*D scaled by 10)
static inline long long w_robot_relay_scaled(const Node& robot, const Node& relay) {
    return 10LL * dist2(robot, relay);
}

static inline string edgeStr(int a, int b) {
    if (a > b) swap(a, b);
    return to_string(a) + "-" + to_string(b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;

    vector<Node> robots;
    vector<Node> relays;
    robots.reserve(N);
    relays.reserve(K);

    for (int i = 0; i < N + K; i++) {
        Node nd;
        cin >> nd.id >> nd.x >> nd.y >> nd.type;
        if (nd.type == 'C') relays.push_back(nd);
        else robots.push_back(nd);
    }

    int n = (int)robots.size();
    int k = (int)relays.size();

    if (n == 0) {
        cout << "#\n#\n";
        return 0;
    }

    // Prim MST over robots
    const long long INF = (1LL << 62);
    vector<long long> best(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);

    best[0] = 0;
    for (int it = 0; it < n; it++) {
        int u = -1;
        long long bd = INF;
        for (int i = 0; i < n; i++) {
            if (!used[i] && best[i] < bd) {
                bd = best[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;
        for (int v = 0; v < n; v++) {
            if (used[v] || v == u) continue;
            long long w = w_robot_robot_scaled(robots[u], robots[v]);
            if (w < best[v]) {
                best[v] = w;
                parent[v] = u;
            }
        }
    }

    vector<pair<int,int>> mstEdgesIdx; // (u, p) as indices in robots
    mstEdgesIdx.reserve(max(0, n - 1));
    for (int v = 1; v < n; v++) {
        if (parent[v] != -1) mstEdgesIdx.push_back({v, parent[v]});
    }

    // Heuristic: replace some MST edges (a-b) with a-c and b-c via a unique relay c if cheaper.
    vector<char> relayUsed(k, 0);
    vector<int> selectedRelayIds;
    vector<string> links;
    links.reserve((n - 1) + min(n - 1, k));

    for (auto [u, p] : mstEdgesIdx) {
        long long orig = w_robot_robot_scaled(robots[u], robots[p]);
        int bestRelay = -1;
        long long bestVia = INF;

        for (int ri = 0; ri < k; ri++) {
            if (relayUsed[ri]) continue;
            long long via = w_robot_relay_scaled(robots[u], relays[ri]) + w_robot_relay_scaled(robots[p], relays[ri]);
            if (via < bestVia) {
                bestVia = via;
                bestRelay = ri;
            }
        }

        if (bestRelay != -1 && bestVia + 0LL < orig) {
            relayUsed[bestRelay] = 1;
            selectedRelayIds.push_back(relays[bestRelay].id);
            links.push_back(edgeStr(robots[u].id, relays[bestRelay].id));
            links.push_back(edgeStr(robots[p].id, relays[bestRelay].id));
        } else {
            links.push_back(edgeStr(robots[u].id, robots[p].id));
        }
    }

    // Output selected relays
    if (selectedRelayIds.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selectedRelayIds.size(); i++) {
            if (i) cout << "#";
            cout << selectedRelayIds[i];
        }
        cout << "\n";
    }

    // Output links
    if (links.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < links.size(); i++) {
            if (i) cout << "#";
            cout << links[i];
        }
        cout << "\n";
    }

    return 0;
}