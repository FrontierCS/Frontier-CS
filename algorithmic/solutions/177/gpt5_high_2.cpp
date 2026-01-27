#include <bits/stdc++.h>
using namespace std;

static inline long long computeCountsAndConflicts(const vector<pair<int,int>>& edges, const vector<int>& color, vector<array<int,3>>& cnt) {
    int n = (int)color.size();
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    long long conflicts = 0;
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        int cu = color[u], cv = color[v];
        cnt[u][cv]++; cnt[v][cu]++;
        if (cu == cv) conflicts++;
    }
    return conflicts;
}

static inline long long localImprove(const vector<vector<int>>& g, vector<int>& color, vector<array<int,3>>& cnt, vector<int>& sizes, const vector<int>& order, std::mt19937& rng, long long conflicts) {
    const int n = (int)color.size();
    const int MAX_PASSES = 1000;
    for (int pass = 0; pass < MAX_PASSES; ++pass) {
        bool improved = false;
        for (int i_idx = 0; i_idx < n; ++i_idx) {
            int i = order[i_idx];
            int cur = color[i];
            int c0 = cnt[i][0], c1 = cnt[i][1], c2 = cnt[i][2];
            int minCnt = c0;
            if (c1 < minCnt) minCnt = c1;
            if (c2 < minCnt) minCnt = c2;
            if (minCnt < cnt[i][cur]) {
                int candidates[3]; int k = 0;
                int minSize = INT_MAX;
                for (int c = 0; c < 3; ++c) {
                    if (cnt[i][c] == minCnt) {
                        if (sizes[c] < minSize) {
                            minSize = sizes[c];
                            k = 0;
                            candidates[k++] = c;
                        } else if (sizes[c] == minSize) {
                            candidates[k++] = c;
                        }
                    }
                }
                int newc = candidates[rng() % k];
                conflicts += cnt[i][newc] - cnt[i][cur];
                for (int v : g[i]) {
                    cnt[v][cur]--;
                    cnt[v][newc]++;
                }
                sizes[cur]--; sizes[newc]++;
                color[i] = newc;
                improved = true;
            }
        }
        if (!improved) break;
    }
    return conflicts;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> g(n);
    g.reserve(n);
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

    // If no edges, trivial solution
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    // Order by degree descending
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    // Random initialization
    vector<int> color_random(n);
    for (int i = 0; i < n; ++i) color_random[i] = rng() % 3;
    vector<array<int,3>> cnt_random(n);
    long long conf_random = computeCountsAndConflicts(edges, color_random, cnt_random);

    // Greedy initialization
    vector<int> color_greedy(n, -1);
    vector<int> sizes(3, 0);
    for (int u : order) {
        int local[3] = {0,0,0};
        for (int v : g[u]) {
            int cv = color_greedy[v];
            if (cv != -1) local[cv]++;
        }
        int minCnt = min(local[0], min(local[1], local[2]));
        int candidates[3]; int k = 0;
        int minSize = INT_MAX;
        for (int c = 0; c < 3; ++c) if (local[c] == minCnt) {
            if (sizes[c] < minSize) {
                minSize = sizes[c];
                k = 0;
                candidates[k++] = c;
            } else if (sizes[c] == minSize) {
                candidates[k++] = c;
            }
        }
        int chosen = candidates[rng() % k];
        color_greedy[u] = chosen;
        sizes[chosen]++;
    }
    vector<array<int,3>> cnt_greedy(n);
    long long conf_greedy = computeCountsAndConflicts(edges, color_greedy, cnt_greedy);

    // Choose better initialization
    vector<int> color;
    vector<array<int,3>> cnt(n);
    long long conflicts;
    if (conf_greedy <= conf_random) {
        color = move(color_greedy);
        cnt = move(cnt_greedy);
        conflicts = conf_greedy;
    } else {
        color = move(color_random);
        cnt = move(cnt_random);
        conflicts = conf_random;
        // recompute sizes for random init
        sizes = {0,0,0};
        for (int i = 0; i < n; ++i) sizes[color[i]]++;
    }

    // Local improvement
    conflicts = localImprove(g, color, cnt, sizes, order, rng, conflicts);

    // Keep best
    vector<int> bestColor = color;
    long long bestConf = conflicts;

    // Perturbation and multiple improvement rounds
    int R = 6;
    int P = max(10, n / 200); // number of nodes to perturb each round
    vector<char> used(n, 0);
    vector<int> picks; picks.reserve(P);

    for (int round = 0; round < R; ++round) {
        // Pick P unique nodes
        fill(used.begin(), used.end(), 0);
        picks.clear();
        while ((int)picks.size() < P) {
            int u = (int)(rng() % n);
            if (!used[u]) {
                used[u] = 1;
                picks.push_back(u);
            }
        }
        // Apply random recoloring to perturb
        for (int u : picks) {
            int oldc = color[u];
            int newc = (oldc + 1 + (int)(rng() & 1)) % 3; // ensure different color
            if (newc == oldc) newc = (newc + 1) % 3;
            conflicts += cnt[u][newc] - cnt[u][oldc];
            for (int v : g[u]) {
                cnt[v][oldc]--;
                cnt[v][newc]++;
            }
            sizes[oldc]--; sizes[newc]++;
            color[u] = newc;
        }
        // Improve again
        conflicts = localImprove(g, color, cnt, sizes, order, rng, conflicts);
        if (conflicts < bestConf) {
            bestConf = conflicts;
            bestColor = color;
        }
    }

    // Output 1-based colors
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestColor[i] + 1);
    }
    cout << '\n';
    return 0;
}