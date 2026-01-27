#include <bits/stdc++.h>
using namespace std;

struct Node {
    int sat;
    int deg;
    int id;
    int stamp;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> g(N);
    vector<vector<unsigned char>> mat(N, vector<unsigned char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();

    int B = (N + 63) >> 6;
    vector<vector<uint64_t>> used(N, vector<uint64_t>(B, 0));
    vector<int> sat(N, 0), stamp(N, 0), color(N, 0);

    auto cmp = [](const Node& a, const Node& b) {
        if (a.sat != b.sat) return a.sat < b.sat;       // higher saturation first
        if (a.deg != b.deg) return a.deg < b.deg;       // higher degree first
        return a.id > b.id;                              // smaller id first
    };
    priority_queue<Node, vector<Node>, decltype(cmp)> pq(cmp);
    for (int i = 0; i < N; ++i) pq.push({0, deg[i], i, 0});

    auto bit_get = [&](const vector<uint64_t>& bits, int c) -> bool {
        int pos = c - 1;
        return (bits[pos >> 6] >> (pos & 63)) & 1ULL;
    };
    auto bit_set = [&](vector<uint64_t>& bits, int c) {
        int pos = c - 1;
        bits[pos >> 6] |= (1ULL << (pos & 63));
    };
    auto choose_color = [&](const vector<uint64_t>& bits) -> int {
        for (int w = 0; w < B; ++w) {
            uint64_t usedw = bits[w];
            if (w == B - 1) {
                int rem = N - (w << 6);
                if (rem < 64) {
                    uint64_t mask = (rem == 64) ? ~0ULL : ((1ULL << rem) - 1ULL);
                    usedw |= ~mask;
                }
            }
            uint64_t inv = ~usedw;
            if (inv) {
                int bit = __builtin_ctzll(inv);
                int pos = (w << 6) + bit;
                if (pos < N) return pos + 1;
            }
        }
        return N; // Fallback, should not happen
    };

    int colored_count = 0;
    int maxColor = 0;

    while (colored_count < N) {
        Node cur;
        bool found = false;
        while (!pq.empty()) {
            cur = pq.top(); pq.pop();
            if (color[cur.id] == 0 && cur.stamp == stamp[cur.id]) {
                found = true;
                break;
            }
        }
        if (!found) {
            int best = -1, bestSat = -1, bestDeg = -1;
            for (int i = 0; i < N; ++i) if (color[i] == 0) {
                if (sat[i] > bestSat || (sat[i] == bestSat && deg[i] > bestDeg) || (sat[i] == bestSat && deg[i] == bestDeg && (best == -1 || i < best))) {
                    best = i; bestSat = sat[i]; bestDeg = deg[i];
                }
            }
            if (best == -1) break;
            cur = {bestSat, bestDeg, best, stamp[best]};
        }

        int v = cur.id;
        int c = choose_color(used[v]);
        color[v] = c;
        if (c > maxColor) maxColor = c;
        ++colored_count;

        for (int u : g[v]) {
            if (color[u] == 0) {
                if (!bit_get(used[u], c)) {
                    bit_set(used[u], c);
                    ++sat[u];
                    ++stamp[u];
                    pq.push({sat[u], deg[u], u, stamp[u]});
                }
            }
        }
    }

    // Simple post-processing: try to reduce colors greedily
    auto reduce_colors_pass = [&](vector<int>& col) -> bool {
        bool changed = false;
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (col[a] != col[b]) return col[a] > col[b];
            return deg[a] > deg[b];
        });
        int currentMax = *max_element(col.begin(), col.end());
        vector<char> usedc(currentMax + 1, 0);
        for (int v : order) {
            fill(usedc.begin(), usedc.end(), 0);
            for (int u : g[v]) {
                int cu = col[u];
                if (cu >= 1 && cu <= currentMax) usedc[cu] = 1;
            }
            int newc = 1;
            while (newc <= currentMax && usedc[newc]) ++newc;
            if (newc < col[v]) {
                col[v] = newc;
                changed = true;
            }
        }
        return changed;
    };

    // Apply a few passes
    for (int it = 0; it < 2; ++it) {
        bool ch = reduce_colors_pass(color);
        if (!ch) break;
    }
    maxColor = *max_element(color.begin(), color.end());

    for (int i = 0; i < N; ++i) {
        if (color[i] <= 0) color[i] = 1;
        cout << color[i] << "\n";
    }

    return 0;
}