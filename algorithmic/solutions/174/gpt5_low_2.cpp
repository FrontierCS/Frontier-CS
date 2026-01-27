#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    adj.reserve(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    // RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)new int;
    std::mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    // Initial greedy coloring
    vector<int> color(n, -1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    for (int v : order) {
        array<int,3> cnt = {0,0,0};
        for (int u : adj[v]) {
            int c = color[u];
            if (c >= 0) cnt[c]++;
        }
        int best = 0;
        int bestVal = cnt[0];
        for (int c = 1; c < 3; ++c) {
            if (cnt[c] < bestVal || (cnt[c] == bestVal && rng()%2)) {
                best = c;
                bestVal = cnt[c];
            }
        }
        color[v] = best;
    }

    // Build neighbor color counts
    vector<array<int,3>> ncnt(n);
    for (int i = 0; i < n; ++i) ncnt[i] = {0,0,0};
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        ncnt[u][color[v]]++;
        ncnt[v][color[u]]++;
    }

    vector<int> conf(n,0);
    vector<int> bads;
    bads.reserve(n);
    vector<int> pos(n, -1);
    auto add_bad = [&](int v){
        if (pos[v] == -1) {
            pos[v] = (int)bads.size();
            bads.push_back(v);
        }
    };
    auto remove_bad = [&](int v){
        int p = pos[v];
        if (p != -1) {
            int last = bads.back();
            bads[p] = last;
            pos[last] = p;
            bads.pop_back();
            pos[v] = -1;
        }
    };

    for (int v = 0; v < n; ++v) {
        conf[v] = ncnt[v][color[v]];
        if (conf[v] > 0) add_bad(v);
    }

    auto now = chrono::steady_clock::now();
    // Time budget ~1.5 seconds
    auto deadline = now + chrono::milliseconds(1500);

    // Min-conflicts local search
    int attempts_since_change = 0;
    int steps = 0;
    while (chrono::steady_clock::now() < deadline) {
        if (bads.empty()) break;

        int v = -1;
        int tries = 0;
        // Try to find a vertex where a different minimal color exists
        while (tries < 20) {
            int idx = (int)(rng() % bads.size());
            int cand = bads[idx];
            array<int,3> cnt = ncnt[cand];
            int cur = color[cand];
            int minv = min(cnt[0], min(cnt[1], cnt[2]));
            // collect minimal colors
            int choices[3], k = 0;
            for (int c = 0; c < 3; ++c) if (cnt[c] == minv) choices[k++] = c;
            if (k > 1 || choices[0] != cur) { v = cand; break; }
            tries++;
        }
        if (v == -1) {
            // Could not find suitable v; random perturbation
            int r = (int)(rng() % n);
            int newc = (int)(rng() % 3);
            if (newc == color[r]) newc = (newc + 1 + (rng()%2)) % 3;
            int oldc = color[r];
            if (oldc != newc) {
                // apply move
                for (int u : adj[r]) {
                    // update neighbor counts
                    ncnt[u][oldc]--;
                    ncnt[u][newc]++;
                    // update neighbor conflicts if necessary
                    if (color[u] == oldc) {
                        conf[u]--;
                        if (conf[u] == 0) remove_bad(u);
                    }
                    if (color[u] == newc) {
                        if (conf[u] == 0) add_bad(u);
                        conf[u]++;
                    }
                }
                color[r] = newc;
                conf[r] = ncnt[r][newc];
                if (conf[r] == 0) remove_bad(r);
                else add_bad(r);
            }
            continue;
        }

        // choose best color for v
        array<int,3> cnt = ncnt[v];
        int cur = color[v];
        int minv = min(cnt[0], min(cnt[1], cnt[2]));
        int choices[3], k = 0;
        for (int c = 0; c < 3; ++c) if (cnt[c] == minv) choices[k++] = c;
        int newc;
        if (k == 1) newc = choices[0];
        else {
            // prefer a color different from current if possible
            int pick = -1;
            for (int i = 0; i < k; ++i) if (choices[i] != cur) { pick = choices[i]; break; }
            if (pick == -1) pick = choices[rng()%k];
            newc = pick;
        }
        if (newc == cur) {
            // no change, skip this step
            attempts_since_change++;
            if (attempts_since_change > 1000) {
                // random shake
                int r = (int)(rng() % n);
                int nc = (int)(rng() % 3);
                if (nc == color[r]) nc = (nc + 1 + (rng()%2)) % 3;
                int oc = color[r];
                if (oc != nc) {
                    for (int u : adj[r]) {
                        ncnt[u][oc]--;
                        ncnt[u][nc]++;
                        if (color[u] == oc) {
                            conf[u]--;
                            if (conf[u] == 0) remove_bad(u);
                        }
                        if (color[u] == nc) {
                            if (conf[u] == 0) add_bad(u);
                            conf[u]++;
                        }
                    }
                    color[r] = nc;
                    conf[r] = ncnt[r][nc];
                    if (conf[r] == 0) remove_bad(r);
                    else add_bad(r);
                }
                attempts_since_change = 0;
            }
            continue;
        }
        // apply move v: cur -> newc
        for (int u : adj[v]) {
            ncnt[u][cur]--;
            ncnt[u][newc]++;
            if (color[u] == cur) {
                conf[u]--;
                if (conf[u] == 0) remove_bad(u);
            }
            if (color[u] == newc) {
                if (conf[u] == 0) add_bad(u);
                conf[u]++;
            }
        }
        color[v] = newc;
        conf[v] = ncnt[v][newc];
        if (conf[v] == 0) remove_bad(v);
        else add_bad(v);
        attempts_since_change = 0;
        steps++;
    }

    // Output colors 1..3
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        int c = color[i];
        if (c < 0) c = 0;
        cout << (c + 1);
    }
    cout << '\n';
    return 0;
}