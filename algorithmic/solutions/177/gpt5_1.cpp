#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastInput() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = read();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = read();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = read();
        }
        for (; c >= '0' && c <= '9'; c = read()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
} In;

static inline uint64_t rng64() {
    static uint64_t x = 88172645463393265ull; // fixed seed for determinism
    x ^= x << 7;
    x ^= x >> 9;
    return x;
}
static inline uint32_t rnd() {
    return (uint32_t)(rng64() & 0xffffffffu);
}
static inline int rndInt(int l, int r) { // inclusive
    return l + (int)(rng64() % (uint64_t)(r - l + 1));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!In.readInt(n)) return 0;
    In.readInt(m);
    vector<vector<int>> g(n);
    g.reserve(n);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        In.readInt(u);
        In.readInt(v);
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
        deg[u]++; deg[v]++;
    }

    // Initial greedy coloring by descending degree
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    vector<uint8_t> color(n, 3); // sentinel 3 = uncolored
    for (int id = 0; id < n; ++id) {
        int v = order[id];
        int cnt[3] = {0, 0, 0};
        for (int u : g[v]) {
            if (color[u] < 3) cnt[color[u]]++;
        }
        int bestVal = cnt[0];
        int bestC = 0;
        for (int c = 1; c < 3; ++c) {
            if (cnt[c] < bestVal) {
                bestVal = cnt[c];
                bestC = c;
            } else if (cnt[c] == bestVal && (rnd() & 1)) {
                bestC = c;
            }
        }
        color[v] = (uint8_t)bestC;
    }

    // Neighbor color counts
    vector<array<int,3>> ncnt(n);
    for (int i = 0; i < n; ++i) ncnt[i] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        uint8_t cv = color[v];
        for (int u : g[v]) {
            uint8_t cu = color[u];
            ncnt[v][cu]++;
        }
    }

    long long b = 0;
    for (int v = 0; v < n; ++v) {
        b += ncnt[v][color[v]];
    }
    b /= 2;

    // Bad set: vertices participating in conflicting edges
    vector<int> bad;
    bad.reserve(n);
    vector<int> pos(n, -1);
    auto add_bad = [&](int v) {
        if (pos[v] == -1) {
            pos[v] = (int)bad.size();
            bad.push_back(v);
        }
    };
    auto rem_bad = [&](int v) {
        int p = pos[v];
        if (p != -1) {
            int last = bad.back();
            bad[p] = last;
            pos[last] = p;
            bad.pop_back();
            pos[v] = -1;
        }
    };
    for (int v = 0; v < n; ++v) {
        if (ncnt[v][color[v]] > 0) add_bad(v);
    }

    long long best_b = b;
    vector<uint8_t> best_color = color;

    if (m > 0 && b > 0) {
        // Min-conflicts local search
        const long long maxSteps = (long long)max(1, min(3000000, m * 15 + n * 10));
        long long steps = 0;
        int noImprove = 0;
        const int noImproveLimit = max(1000, n / 3);

        while (steps < maxSteps && b > 0) {
            int v;
            if (!bad.empty()) {
                int idx = (int)(rng64() % (uint64_t)bad.size());
                v = bad[idx];
            } else {
                v = (int)(rng64() % (uint64_t)n);
            }

            // Choose best color for v
            int cnt0 = ncnt[v][0];
            int cnt1 = ncnt[v][1];
            int cnt2 = ncnt[v][2];

            int bestVal = cnt0;
            int bestC = 0;
            if (cnt1 < bestVal || (cnt1 == bestVal && (rng64() & 1))) { bestVal = cnt1; bestC = 1; }
            if (cnt2 < bestVal || (cnt2 == bestVal && (rng64() & 1))) { bestVal = cnt2; bestC = 2; }

            uint8_t oldc = color[v];
            uint8_t newc = (uint8_t)bestC;

            // To escape plateaus, sometimes pick a different color among ties
            if (bestVal == ncnt[v][oldc]) {
                // 1/16 chance to switch to another color with same min value
                if ((rng64() & 15ull) == 0ull) {
                    int choices[2], k = 0;
                    for (int c = 0; c < 3; ++c) {
                        if (c != oldc && ncnt[v][c] == bestVal) choices[k++] = c;
                    }
                    if (k > 0) newc = (uint8_t)choices[rndInt(0, k - 1)];
                }
            }

            if (newc != oldc) {
                long long delta = (long long)ncnt[v][newc] - (long long)ncnt[v][oldc];
                b += delta;

                // Update neighbors
                for (int u : g[v]) {
                    ncnt[u][oldc]--;
                    ncnt[u][newc]++;
                    if (ncnt[u][color[u]] > 0) add_bad(u); else rem_bad(u);
                }

                color[v] = newc;
                if (ncnt[v][newc] > 0) add_bad(v); else rem_bad(v);

                if (b < best_b) {
                    best_b = b;
                    best_color = color;
                    noImprove = 0;
                    if (best_b == 0) break;
                } else {
                    noImprove++;
                    if (noImprove > noImproveLimit) {
                        // Small random shake: reassign a few random vertices to min-conflict colors
                        int shakes = max(1, n / 500);
                        for (int t = 0; t < shakes; ++t) {
                            int x = (int)(rng64() % (uint64_t)n);
                            int c0 = ncnt[x][0], c1 = ncnt[x][1], c2 = ncnt[x][2];
                            int vbest = c0, vcol = 0;
                            if (c1 < vbest || (c1 == vbest && (rng64() & 1))) { vbest = c1; vcol = 1; }
                            if (c2 < vbest || (c2 == vbest && (rng64() & 1))) { vbest = c2; vcol = 2; }
                            uint8_t ox = color[x];
                            if (ox != vcol) {
                                long long d = (long long)ncnt[x][vcol] - (long long)ncnt[x][ox];
                                b += d;
                                for (int y : g[x]) {
                                    ncnt[y][ox]--;
                                    ncnt[y][vcol]++;
                                    if (ncnt[y][color[y]] > 0) add_bad(y); else rem_bad(y);
                                }
                                color[x] = (uint8_t)vcol;
                                if (ncnt[x][vcol] > 0) add_bad(x); else rem_bad(x);
                                if (b < best_b) {
                                    best_b = b;
                                    best_color = color;
                                }
                            }
                        }
                        noImprove = 0;
                    }
                }
            } else {
                noImprove++;
                if (noImprove > noImproveLimit) {
                    int shakes = max(1, n / 500);
                    for (int t = 0; t < shakes; ++t) {
                        int x = (int)(rng64() % (uint64_t)n);
                        int c0 = ncnt[x][0], c1 = ncnt[x][1], c2 = ncnt[x][2];
                        int vbest = c0, vcol = 0;
                        if (c1 < vbest || (c1 == vbest && (rng64() & 1))) { vbest = c1; vcol = 1; }
                        if (c2 < vbest || (c2 == vbest && (rng64() & 1))) { vbest = c2; vcol = 2; }
                        uint8_t ox = color[x];
                        if (ox != vcol) {
                            long long d = (long long)ncnt[x][vcol] - (long long)ncnt[x][ox];
                            b += d;
                            for (int y : g[x]) {
                                ncnt[y][ox]--;
                                ncnt[y][vcol]++;
                                if (ncnt[y][color[y]] > 0) add_bad(y); else rem_bad(y);
                            }
                            color[x] = (uint8_t)vcol;
                            if (ncnt[x][vcol] > 0) add_bad(x); else rem_bad(x);
                            if (b < best_b) {
                                best_b = b;
                                best_color = color;
                            }
                        }
                    }
                    noImprove = 0;
                }
            }
            ++steps;
        }
    }

    // Output best found
    const vector<uint8_t> &ans = best_color;
    for (int i = 0; i < n; ++i) {
        int c = (int)ans[i] + 1;
        if (i) cout << ' ';
        cout << c;
    }
    cout << '\n';
    return 0;
}