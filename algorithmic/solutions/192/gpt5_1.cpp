#include <bits/stdc++.h>
using namespace std;

struct Node {
    int gain;
    int id;
    int ver;
    bool operator<(const Node& other) const {
        if (gain != other.gain) return gain < other.gain; // max-heap by gain
        return id < other.id;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> g(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto computeCounts = [&](const vector<uint8_t>& s, vector<int>& across, vector<int>& gain, int& cut) {
        fill(across.begin(), across.end(), 0);
        cut = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (s[u] != s[v]) {
                cut++;
                across[u]++;
                across[v]++;
            }
        }
        for (int i = 0; i < n; ++i) {
            gain[i] = deg[i] - 2 * across[i];
        }
    };

    auto improveLocal = [&](vector<uint8_t>& s, vector<int>& across, vector<int>& gain, int cut) -> int {
        int N = n;
        vector<int> ver(N, 0);
        priority_queue<Node> pq;
        pq = priority_queue<Node>();
        for (int i = 0; i < N; ++i) {
            pq.push({gain[i], i, ver[i]});
        }
        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            int v = cur.id;
            if (cur.ver != ver[v]) continue;
            if (cur.gain != gain[v]) continue;
            if (cur.gain <= 0) break;
            int oldAcross = across[v];
            cut += gain[v];
            s[v] ^= 1;
            across[v] = deg[v] - oldAcross;
            gain[v] = deg[v] - 2 * across[v];
            ver[v]++;
            pq.push({gain[v], v, ver[v]});
            for (int u : g[v]) {
                if (s[u] == s[v]) {
                    across[u]--;
                } else {
                    across[u]++;
                }
                gain[u] = deg[u] - 2 * across[u];
                ver[u]++;
                pq.push({gain[u], u, ver[u]});
            }
        }
        return cut;
    };

    auto greedyInitial = [&](void) -> vector<uint8_t> {
        vector<uint8_t> s(n, 0);
        vector<char> assigned(n, 0);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int c0 = 0, c1 = 0;
            for (int u : g[v]) {
                if (assigned[u]) {
                    if (s[u] == 0) c0++;
                    else c1++;
                }
            }
            if (c0 > c1) s[v] = 1;
            else if (c1 > c0) s[v] = 0;
            else s[v] = (uint8_t)(rng() & 1);
            assigned[v] = 1;
        }
        return s;
    };

    auto randomInitial = [&](void) -> vector<uint8_t> {
        vector<uint8_t> s(n);
        for (int i = 0; i < n; ++i) s[i] = (uint8_t)(rng() & 1);
        return s;
    };

    vector<uint8_t> bestS(n, 0), workS(n, 0);
    vector<int> across(n, 0), gain(n, 0);
    int cut = 0, bestCut = -1;

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.80; // seconds

    // Try a few different initializations and take the best after local improvement
    vector<vector<uint8_t>> initials;
    initials.push_back(greedyInitial());
    initials.push_back(randomInitial());
    // Another greedy with different random order
    initials.push_back(greedyInitial());
    // Another random
    initials.push_back(randomInitial());

    for (auto &initS : initials) {
        workS = initS;
        computeCounts(workS, across, gain, cut);
        cut = improveLocal(workS, across, gain, cut);
        if (cut > bestCut) {
            bestCut = cut;
            bestS = workS;
        }
        if (chrono::duration<double>(chrono::steady_clock::now() - start).count() > TIME_LIMIT) break;
    }

    // Shake and re-optimize while time remains
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    while (chrono::duration<double>(chrono::steady_clock::now() - start).count() < TIME_LIMIT) {
        workS = bestS;
        shuffle(idx.begin(), idx.end(), rng);
        double p = std::uniform_real_distribution<double>(0.01, 0.15)(rng);
        int R = max(1, (int)(n * p));
        for (int i = 0; i < R; ++i) {
            workS[idx[i]] ^= 1;
        }
        computeCounts(workS, across, gain, cut);
        cut = improveLocal(workS, across, gain, cut);
        if (cut > bestCut) {
            bestCut = cut;
            bestS = workS;
        }
        // Optional: occasional larger shake
        if (chrono::duration<double>(chrono::steady_clock::now() - start).count() > TIME_LIMIT) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestS[i];
    }
    cout << '\n';
    return 0;
}