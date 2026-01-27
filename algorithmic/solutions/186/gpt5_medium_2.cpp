#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 512;
static const int MAXC = 512;

int dsatur_color(const vector<vector<int>>& adj, vector<int>& color, vector<int>& ds_order) {
    int N = (int)adj.size();
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    vector<bitset<MAXC>> satmask(N);
    vector<int> satdeg(N, 0);
    color.assign(N, -1);
    ds_order.clear();
    ds_order.reserve(N);
    int used_colors = 0;

    vector<char> uncolored(N, 1);

    for (int it = 0; it < N; ++it) {
        int best = -1, bestSat = -1, bestDeg = -1;
        for (int v = 0; v < N; ++v) if (uncolored[v]) {
            int s = satdeg[v];
            if (s > bestSat || (s == bestSat && deg[v] > bestDeg)) {
                bestSat = s; bestDeg = deg[v]; best = v;
            }
        }
        int c = 1;
        while (c <= used_colors && satmask[best].test(c)) ++c;
        if (c == used_colors + 1) ++used_colors;
        color[best] = c;
        uncolored[best] = 0;
        ds_order.push_back(best);
        for (int u : adj[best]) if (uncolored[u]) {
            if (!satmask[u].test(c)) {
                satmask[u].set(c);
                ++satdeg[u];
            }
        }
    }
    return used_colors;
}

bool greedy_limit_color(const vector<vector<int>>& adj, const vector<int>& order, int K, vector<int>& outColors) {
    int N = (int)adj.size();
    vector<int> color(N, 0);
    vector<char> used(K + 1);
    for (int v : order) {
        if (K < 1) return false;
        fill(used.begin(), used.end(), 0);
        for (int u : adj[v]) {
            int c = color[u];
            if (c >= 1 && c <= K) used[c] = 1;
        }
        int c = 1;
        while (c <= K && used[c]) ++c;
        if (c > K) return false;
        color[v] = c;
    }
    outColors = move(color);
    return true;
}

int greedy_unlimited(const vector<vector<int>>& adj, const vector<int>& order, vector<int>& outColors) {
    int N = (int)adj.size();
    vector<int> color(N, 0);
    int maxC = 0;
    vector<char> used;
    for (int v : order) {
        used.assign(maxC + 2, 0);
        for (int u : adj[v]) {
            int c = color[u];
            if (c >= 1 && c <= maxC + 1) used[c] = 1;
        }
        int c = 1;
        while (c <= maxC && used[c]) ++c;
        if (c == maxC + 1) ++maxC;
        color[v] = c;
    }
    outColors = move(color);
    return maxC;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXN>> mat(N);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v || u < 0 || v < 0 || u >= N || v >= N) continue;
        mat[u].set(v);
        mat[v].set(u);
    }
    vector<vector<int>> adj(N);
    for (int i = 0; i < N; ++i) {
        for (int j = i + 1; j < N; ++j) {
            if (mat[i].test(j)) {
                adj[i].push_back(j);
                adj[j].push_back(i);
            }
        }
    }

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds

    // Initial DSATUR coloring
    vector<int> bestColors, ds_order;
    int bestC = dsatur_color(adj, bestColors, ds_order);

    // Prepare base orders
    vector<int> deg(N), id(N);
    for (int i = 0; i < N; ++i) { deg[i] = (int)adj[i].size(); id[i] = i; }
    vector<int> order_deg_desc = id;
    sort(order_deg_desc.begin(), order_deg_desc.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });
    vector<int> order_deg_asc = id;
    sort(order_deg_asc.begin(), order_deg_asc.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });
    vector<int> order_ds = ds_order;
    vector<int> order_ds_rev = ds_order;
    reverse(order_ds_rev.begin(), order_ds_rev.end());

    vector<vector<int>> baseOrders = {order_deg_desc, order_ds, order_ds_rev, order_deg_asc};

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    vector<int> tmpColors;
    int iter = 0;

    auto elapsed = [&](){
        chrono::duration<double> diff = chrono::steady_clock::now() - start;
        return diff.count();
    };

    while (elapsed() < TIME_LIMIT) {
        for (auto base : baseOrders) {
            if (elapsed() >= TIME_LIMIT) break;

            // Try limited coloring to reduce color count by 1
            if (bestC > 1) {
                if (greedy_limit_color(adj, base, bestC - 1, tmpColors)) {
                    bestC = bestC - 1;
                    bestColors = tmpColors;
                    if (bestC <= 1) break;
                }
            }

            // Randomized attempts based on this base
            for (int t = 0; t < 3 && elapsed() < TIME_LIMIT; ++t) {
                shuffle(base.begin(), base.end(), rng);
                if (bestC > 1 && greedy_limit_color(adj, base, bestC - 1, tmpColors)) {
                    bestC = bestC - 1;
                    bestColors = tmpColors;
                    if (bestC <= 1) break;
                } else if ((iter & 7) == 0) {
                    // Occasionally try unlimited greedy to possibly beat DSATUR
                    int used = greedy_unlimited(adj, base, tmpColors);
                    if (used < bestC) {
                        bestC = used;
                        bestColors = tmpColors;
                    }
                }
                ++iter;
            }
        }
        if (bestC <= 1) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << bestColors[i] << "\n";
    }
    return 0;
}