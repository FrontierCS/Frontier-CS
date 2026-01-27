#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 500;
static const int MAXC = 512;

struct ColoringResult {
    vector<int> color;
    int k;
};

static inline double elapsed_seconds(const chrono::steady_clock::time_point& st) {
    return chrono::duration<double>(chrono::steady_clock::now() - st).count();
}

ColoringResult dsatur_color(const vector<vector<int>>& g, const vector<int>& deg, mt19937& rng) {
    int n = (int)g.size();
    vector<int> color(n, 0);
    vector<int> satCount(n, 0);
    vector<bitset<MAXC>> satMask(n);
    vector<char> colored(n, 0);

    int coloredCnt = 0;
    int curMaxColor = 0;

    vector<int> seen(MAXC, 0);
    int stamp = 1;

    while (coloredCnt < n) {
        int bestSat = -1, bestDeg = -1;
        vector<int> cand;
        cand.reserve(n);

        for (int v = 0; v < n; v++) {
            if (colored[v]) continue;
            int s = satCount[v];
            int d = deg[v];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                bestSat = s;
                bestDeg = d;
                cand.clear();
                cand.push_back(v);
            } else if (s == bestSat && d == bestDeg) {
                cand.push_back(v);
            }
        }

        int v;
        if ((int)cand.size() == 1) v = cand[0];
        else v = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];

        ++stamp;
        if (stamp == INT_MAX) {
            fill(seen.begin(), seen.end(), 0);
            stamp = 1;
        }

        for (int u : g[v]) {
            int cu = color[u];
            if (cu > 0) seen[cu] = stamp;
        }

        int chosen = 1;
        int limit = curMaxColor + 1;
        for (; chosen <= limit; chosen++) {
            if (seen[chosen] != stamp) break;
        }

        color[v] = chosen;
        if (chosen > curMaxColor) curMaxColor = chosen;
        colored[v] = 1;
        coloredCnt++;

        for (int u : g[v]) {
            if (colored[u]) continue;
            if (!satMask[u].test(chosen)) {
                satMask[u].set(chosen);
                satCount[u]++;
            }
        }
    }

    return {color, curMaxColor};
}

static inline int compute_max_color(const vector<int>& col) {
    int mx = 0;
    for (int c : col) mx = max(mx, c);
    return mx;
}

bool try_eliminate_color(vector<int>& col, int targetColor, const vector<vector<int>>& g, mt19937& rng, double& timeBudget, const chrono::steady_clock::time_point& st) {
    int n = (int)g.size();
    if (targetColor <= 1) return true;

    vector<int> vertices;
    vertices.reserve(n);
    for (int i = 0; i < n; i++) if (col[i] == targetColor) vertices.push_back(i);
    if (vertices.empty()) return true;

    vector<int> backup;
    vector<int> freq(targetColor + 1, 0);
    vector<int> seen(MAXC, 0);
    int stamp = 1;

    int attempts = 120;
    if ((int)vertices.size() > 80) attempts = 80;
    if ((int)vertices.size() > 160) attempts = 50;

    for (int a = 0; a < attempts; a++) {
        if (elapsed_seconds(st) > timeBudget) return false;

        backup = col;
        fill(freq.begin(), freq.end(), 0);
        for (int i = 0; i < n; i++) {
            int c = col[i];
            if (c > 0 && c <= targetColor) freq[c]++;
        }

        auto vlist = vertices;
        shuffle(vlist.begin(), vlist.end(), rng);

        bool ok = true;
        for (int v : vlist) {
            ++stamp;
            if (stamp == INT_MAX) {
                fill(seen.begin(), seen.end(), 0);
                stamp = 1;
            }
            for (int u : g[v]) {
                int cu = col[u];
                if (cu > 0 && cu < targetColor) seen[cu] = stamp;
            }

            int bestColor = 0;
            int bestFreq = INT_MAX;
            for (int c = 1; c < targetColor; c++) {
                if (seen[c] == stamp) continue;
                if (freq[c] < bestFreq) {
                    bestFreq = freq[c];
                    bestColor = c;
                    if (bestFreq == 0) break;
                }
            }

            if (bestColor == 0) {
                ok = false;
                break;
            }

            col[v] = bestColor;
            freq[targetColor]--;
            freq[bestColor]++;
        }

        if (ok) return true;
        col.swap(backup);
    }

    return false;
}

void compress_colors(vector<int>& col) {
    int n = (int)col.size();
    int mx = compute_max_color(col);
    vector<int> mp(mx + 1, 0);
    int nid = 0;
    for (int i = 0; i < n; i++) {
        int c = col[i];
        if (mp[c] == 0) mp[c] = ++nid;
        col[i] = mp[c];
    }
}

bool is_valid_coloring(const vector<int>& col, const vector<pair<int,int>>& edges) {
    for (auto [u, v] : edges) {
        if (col[u] == col[v]) return false;
    }
    for (int c : col) if (c <= 0) return false;
    return true;
}

vector<int> safe_greedy(const vector<vector<int>>& g, const vector<int>& deg) {
    int n = (int)g.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    vector<int> col(n, 0);
    vector<int> seen(MAXC, 0);
    int stamp = 1;
    int curMax = 0;

    for (int v : order) {
        ++stamp;
        if (stamp == INT_MAX) {
            fill(seen.begin(), seen.end(), 0);
            stamp = 1;
        }
        for (int u : g[v]) {
            int cu = col[u];
            if (cu > 0) seen[cu] = stamp;
        }
        int chosen = 1;
        while (chosen < MAXC && seen[chosen] == stamp) chosen++;
        if (chosen >= MAXC) chosen = ++curMax;
        col[v] = chosen;
        curMax = max(curMax, chosen);
    }
    compress_colors(col);
    return col;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<bitset<MAXN>> adj(N);
    vector<vector<int>> g(N);
    vector<pair<int,int>> edges;
    edges.reserve(M);

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!adj[u].test(v)) {
            adj[u].set(v);
            adj[v].set(u);
            g[u].push_back(v);
            g[v].push_back(u);
            edges.push_back({u, v});
        }
    }

    vector<int> deg(N);
    for (int i = 0; i < N; i++) deg[i] = (int)g[i].size();

    auto st = chrono::steady_clock::now();
    double timeBudget = 1.92;

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 13);
    seed ^= (seed >> 7);
    seed ^= (seed << 17);
    mt19937 rng((uint32_t)seed);

    vector<int> bestCol;
    int bestK = INT_MAX;

    int runs = 0;
    int maxRuns = 60;
    while (runs < maxRuns && elapsed_seconds(st) < 0.85) {
        auto res = dsatur_color(g, deg, rng);
        int k = res.k;
        if (k < bestK) {
            bestK = k;
            bestCol = std::move(res.color);
            if (bestK <= 2) break;
        }
        runs++;
    }

    if (bestCol.empty()) {
        auto res = dsatur_color(g, deg, rng);
        bestCol = std::move(res.color);
        bestK = res.k;
    }

    compress_colors(bestCol);
    bestK = compute_max_color(bestCol);

    int c = bestK;
    while (c >= 2 && elapsed_seconds(st) < timeBudget) {
        bool ok = try_eliminate_color(bestCol, c, g, rng, timeBudget, st);
        if (ok) {
            compress_colors(bestCol);
            bestK = compute_max_color(bestCol);
            c = bestK;
        } else {
            c--;
        }
    }

    if (!is_valid_coloring(bestCol, edges)) {
        bestCol = safe_greedy(g, deg);
        if (!is_valid_coloring(bestCol, edges)) {
            // Absolute fallback: assign unique colors
            bestCol.resize(N);
            for (int i = 0; i < N; i++) bestCol[i] = i + 1;
        }
    }

    for (int i = 0; i < N; i++) {
        cout << bestCol[i] << "\n";
    }
    return 0;
}