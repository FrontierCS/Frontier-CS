#include <bits/stdc++.h>
using namespace std;

struct Node {
    int gain;
    int id;
    int ver;
    bool operator<(const Node& o) const {
        return gain < o.gain;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();

    vector<int> best_side(n, 0);
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    auto compute_cut = [&](const vector<int>& side) -> int {
        int c = 0;
        for (auto &e : edges) {
            if (side[e.first] ^ side[e.second]) c++;
        }
        return c;
    };

    unsigned seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uintptr_t)&seed;
    std::mt19937 rng(seed);

    vector<int> side(n);
    int best_cut = -1;

    auto do_FM_pass = [&](vector<int>& side, int& cut) -> bool {
        int n2 = (int)side.size();
        vector<int> gain(n2);
        vector<char> locked(n2, 0);
        vector<int> version(n2, 0);

        for (int v = 0; v < n2; ++v) {
            int d_diff = 0;
            for (int u : adj[v]) d_diff += (side[u] != side[v]);
            gain[v] = (int)adj[v].size() - 2 * d_diff;
        }

        priority_queue<Node> pq;
        for (int v = 0; v < n2; ++v) pq.push(Node{gain[v], v, version[v]});

        vector<int> seq; seq.reserve(n2);
        vector<int> gsel; gsel.reserve(n2);
        int cum = 0;
        int bestCum = numeric_limits<int>::min();
        int bestStep = -1;
        int steps = 0;
        Node cur;

        while (steps < n2) {
            bool found = false;
            while (!pq.empty()) {
                cur = pq.top(); pq.pop();
                int id = cur.id;
                if (locked[id]) continue;
                if (cur.ver != version[id]) continue;
                found = true;
                break;
            }
            if (!found) break;

            int v = cur.id;
            locked[v] = 1;
            seq.push_back(v);
            gsel.push_back(gain[v]);
            cum += gain[v];
            if (steps == 0 || cum > bestCum) { bestCum = cum; bestStep = steps; }

            side[v] ^= 1;

            for (int u : adj[v]) {
                if (!locked[u]) {
                    version[u]++;
                    if (side[u] == side[v]) gain[u] += 2;
                    else gain[u] -= 2;
                    pq.push(Node{gain[u], u, version[u]});
                }
            }
            steps++;
        }

        if (bestCum <= 0) {
            for (int i = (int)seq.size() - 1; i >= 0; --i) side[seq[i]] ^= 1;
            return false;
        } else {
            for (int i = (int)seq.size() - 1; i >= bestStep + 1; --i) side[seq[i]] ^= 1;
            cut += bestCum;
            return true;
        }
    };

    auto startTime = chrono::steady_clock::now();
    const double timeLimitSec = 0.95;
    auto deadline = startTime + chrono::duration<double>(timeLimitSec);

    int restart = 0;
    while (chrono::steady_clock::now() < deadline) {
        for (int i = 0; i < n; ++i) side[i] = (int)(rng() & 1u);
        int cut = compute_cut(side);

        int passCount = 0;
        while (chrono::steady_clock::now() < deadline) {
            bool improved = do_FM_pass(side, cut);
            passCount++;
            if (!improved) break;
            if (cut >= m) break;
            if (passCount >= 50) break;
        }

        if (cut > best_cut) {
            best_cut = cut;
            best_side = side;
            if (cut >= m) break;
        }
        restart++;
        if (restart >= 100) break;
    }

    if (best_cut < 0) {
        for (int i = 0; i < n; ++i) best_side[i] = i & 1;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_side[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}