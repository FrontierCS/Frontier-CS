#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> degCount(N, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N || u == v) continue;
        edges.emplace_back(u, v);
        degCount[u]++;
        degCount[v]++;
    }
    M = (int)edges.size();

    vector<vector<int>> adj(N);
    for (int i = 0; i < N; ++i) adj[i].reserve(degCount[i]);
    for (auto &e : edges) {
        adj[e.first].push_back(e.second);
        adj[e.second].push_back(e.first);
    }

    // Leaf reduction
    vector<char> active(N, true);
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    queue<int> q;
    for (int i = 0; i < N; ++i) if (active[i] && deg[i] == 1) q.push(i);

    vector<char> selected(N, false);

    auto remove_vertex = [&](int x) {
        if (!active[x]) return;
        active[x] = false;
        for (int y : adj[x]) {
            if (active[y]) {
                deg[y]--;
                if (deg[y] == 1) q.push(y);
            }
        }
        deg[x] = 0;
    };

    while (!q.empty()) {
        int v = q.front(); q.pop();
        if (!active[v] || deg[v] != 1) continue;
        int u = -1;
        for (int w : adj[v]) {
            if (active[w]) { u = w; break; }
        }
        if (u == -1) {
            // No active neighbor; isolate
            remove_vertex(v);
            continue;
        }
        if (active[u]) {
            selected[u] = true;
            remove_vertex(u);
        }
        if (active[v]) remove_vertex(v);
    }
    for (int i = 0; i < N; ++i) if (active[i] && deg[i] == 0) active[i] = false;

    // Matching on core
    vector<int> order;
    order.reserve(N);
    for (int i = 0; i < N; ++i) if (active[i]) order.push_back(i);

    // Sort by degree descending (current deg)
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return adj[a].size() > adj[b].size();
    });

    vector<char> unmatched(N, false);
    for (int i = 0; i < N; ++i) unmatched[i] = active[i];

    for (int u : order) {
        if (!unmatched[u]) continue;
        for (int v : adj[u]) {
            if (unmatched[v]) {
                selected[u] = true;
                selected[v] = true;
                unmatched[u] = false;
                unmatched[v] = false;
                break;
            }
        }
    }

    // Improvement passes: prune and swaps
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto prune_pass = [&]() -> bool {
        bool changed = false;
        vector<int> sel_list;
        sel_list.reserve(N);
        for (int i = 0; i < N; ++i) if (selected[i]) sel_list.push_back(i);
        shuffle(sel_list.begin(), sel_list.end(), rng);
        for (int v : sel_list) {
            if (!selected[v]) continue;
            bool canRemove = true;
            for (int u : adj[v]) {
                if (!selected[u]) { canRemove = false; break; }
            }
            if (canRemove) {
                selected[v] = false;
                changed = true;
            }
        }
        return changed;
    };

    auto swap_pass = [&]() -> bool {
        bool changed = false;
        vector<int> sel_list;
        sel_list.reserve(N);
        for (int i = 0; i < N; ++i) if (selected[i]) sel_list.push_back(i);
        shuffle(sel_list.begin(), sel_list.end(), rng);
        for (int v : sel_list) {
            if (!selected[v]) continue;
            int uniqueU = -1;
            bool more = false;
            for (int u : adj[v]) {
                if (!selected[u]) {
                    if (uniqueU == -1 || uniqueU == u) uniqueU = u;
                    else { more = true; break; }
                }
            }
            if (!more && uniqueU != -1) {
                // swap v out, uniqueU in
                selected[v] = false;
                selected[uniqueU] = true;
                changed = true;
            }
        }
        return changed;
    };

    // Run a few improvement rounds
    for (int rounds = 0; rounds < 3; ++rounds) {
        bool ch1 = prune_pass();
        bool ch2 = swap_pass();
        bool ch3 = prune_pass();
        if (!(ch1 || ch2 || ch3)) break;
    }

    // Repair coverage: ensure all edges are covered
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        if (!selected[u] && !selected[v]) {
            // pick one endpoint, prefer higher degree
            if (adj[u].size() >= adj[v].size()) selected[u] = true;
            else selected[v] = true;
        }
    }

    // Final prune passes
    for (int rounds = 0; rounds < 2; ++rounds) {
        bool ch = prune_pass();
        if (!ch) break;
    }

    // Output N lines 0/1
    for (int i = 0; i < N; ++i) {
        cout << (selected[i] ? 1 : 0) << '\n';
    }

    return 0;
}