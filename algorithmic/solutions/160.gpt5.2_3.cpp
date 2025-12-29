#include <bits/stdc++.h>
using namespace std;

struct Grid {
    array<uint8_t, 100> c{};
};

static inline Grid tilt(const Grid& g, int dir) {
    // dir: 0=L, 1=R, 2=F, 3=B
    Grid ng;
    ng.c.fill(0);

    if (dir == 0) { // L
        for (int r = 0; r < 10; r++) {
            int w = 0;
            int base = r * 10;
            for (int col = 0; col < 10; col++) {
                uint8_t v = g.c[base + col];
                if (v) ng.c[base + (w++)] = v;
            }
        }
    } else if (dir == 1) { // R
        for (int r = 0; r < 10; r++) {
            int w = 9;
            int base = r * 10;
            for (int col = 9; col >= 0; col--) {
                uint8_t v = g.c[base + col];
                if (v) ng.c[base + (w--)] = v;
            }
        }
    } else if (dir == 2) { // F (towards row 0)
        for (int col = 0; col < 10; col++) {
            int w = 0;
            for (int r = 0; r < 10; r++) {
                uint8_t v = g.c[r * 10 + col];
                if (v) ng.c[(w++) * 10 + col] = v;
            }
        }
    } else { // B (towards row 9)
        for (int col = 0; col < 10; col++) {
            int w = 9;
            for (int r = 9; r >= 0; r--) {
                uint8_t v = g.c[r * 10 + col];
                if (v) ng.c[(w--) * 10 + col] = v;
            }
        }
    }
    return ng;
}

static inline void placeCandy(Grid& g, int p, int flavor) {
    int cnt = 0;
    for (int idx = 0; idx < 100; idx++) {
        if (g.c[idx] == 0) {
            cnt++;
            if (cnt == p) {
                g.c[idx] = (uint8_t)flavor;
                return;
            }
        }
    }
}

struct Targets {
    int tr[4]{}, tc[4]{};
};

static inline long long evalGrid(const Grid& g, int t, const Targets& tg) {
    long long compScore = 0;
    long long adjSame = 0;
    long long adjDiff = 0;
    long long regionScore = 0;

    // adjacency + region
    for (int r = 0; r < 10; r++) {
        for (int c = 0; c < 10; c++) {
            uint8_t v = g.c[r * 10 + c];
            if (!v) continue;
            regionScore -= llabs(r - tg.tr[v]) + llabs(c - tg.tc[v]);
            if (c + 1 < 10) {
                uint8_t u = g.c[r * 10 + (c + 1)];
                if (u) {
                    if (u == v) adjSame++;
                    else adjDiff++;
                }
            }
            if (r + 1 < 10) {
                uint8_t u = g.c[(r + 1) * 10 + c];
                if (u) {
                    if (u == v) adjSame++;
                    else adjDiff++;
                }
            }
        }
    }

    // connected components (4-neigh, same flavor)
    uint8_t vis[100]{};
    int q[100];
    for (int i = 0; i < 100; i++) {
        uint8_t v = g.c[i];
        if (!v || vis[i]) continue;
        vis[i] = 1;
        int head = 0, tail = 0;
        q[tail++] = i;
        int sz = 0;
        while (head < tail) {
            int cur = q[head++];
            sz++;
            int r = cur / 10;
            int c = cur % 10;

            int ni;
            if (r > 0) {
                ni = cur - 10;
                if (!vis[ni] && g.c[ni] == v) vis[ni] = 1, q[tail++] = ni;
            }
            if (r < 9) {
                ni = cur + 10;
                if (!vis[ni] && g.c[ni] == v) vis[ni] = 1, q[tail++] = ni;
            }
            if (c > 0) {
                ni = cur - 1;
                if (!vis[ni] && g.c[ni] == v) vis[ni] = 1, q[tail++] = ni;
            }
            if (c < 9) {
                ni = cur + 1;
                if (!vis[ni] && g.c[ni] == v) vis[ni] = 1, q[tail++] = ni;
            }
        }
        compScore += 1LL * sz * sz;
    }

    long long CW = 2000 + 50LL * t;          // component weight increases
    long long AW = 500;                      // adjacency same
    long long RW = 200LL * (101 - t);        // region weight decreases
    long long DW = 150LL * (101 - t);        // diff adjacency penalty decreases

    return compScore * CW + adjSame * AW + regionScore * RW - adjDiff * DW;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(101);
    for (int t = 1; t <= 100; t++) {
        if (!(cin >> f[t])) return 0;
    }

    int cnt[4] = {0, 0, 0, 0};
    for (int t = 1; t <= 100; t++) cnt[f[t]]++;

    vector<int> flav = {1, 2, 3};
    stable_sort(flav.begin(), flav.end(), [&](int a, int b) {
        if (cnt[a] != cnt[b]) return cnt[a] > cnt[b];
        return a < b;
    });

    // corners: (0,0), (0,9), (9,0)
    pair<int,int> corners[3] = {{0,0}, {0,9}, {9,0}};
    Targets tg;
    for (int i = 0; i < 3; i++) {
        tg.tr[flav[i]] = corners[i].first;
        tg.tc[flav[i]] = corners[i].second;
    }

    Grid cur;
    cur.c.fill(0);

    const char dirChar[4] = {'L', 'R', 'F', 'B'};
    const double gamma = 0.60;

    for (int t = 1; t <= 100; t++) {
        int p;
        if (!(cin >> p)) break;

        Grid placed = cur;
        placeCandy(placed, p, f[t]);

        if (t == 100) {
            // output can be omitted safely
            break;
        }

        double bestTotal = -1e300;
        int bestDir = 0;

        for (int d1 = 0; d1 < 4; d1++) {
            Grid g1 = tilt(placed, d1);
            double total = (double)evalGrid(g1, t, tg);

            // 1-step exact expectation over uniform random next placement
            int nextFlavor = f[t + 1];
            vector<int> empties;
            empties.reserve(100 - t);
            for (int i = 0; i < 100; i++) if (g1.c[i] == 0) empties.push_back(i);

            if (!empties.empty()) {
                double sumBest = 0.0;
                for (int pos : empties) {
                    Grid g2 = g1;
                    g2.c[pos] = (uint8_t)nextFlavor;

                    long long bestH2 = LLONG_MIN;
                    for (int d2 = 0; d2 < 4; d2++) {
                        Grid g3 = tilt(g2, d2);
                        long long h2 = evalGrid(g3, t + 1, tg);
                        if (h2 > bestH2) bestH2 = h2;
                    }
                    sumBest += (double)bestH2;
                }
                total += gamma * (sumBest / (double)empties.size());
            }

            if (total > bestTotal) {
                bestTotal = total;
                bestDir = d1;
            }
        }

        cout << dirChar[bestDir] << '\n' << flush;
        cur = tilt(placed, bestDir);
    }

    return 0;
}