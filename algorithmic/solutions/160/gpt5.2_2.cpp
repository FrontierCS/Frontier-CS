#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 10;
static constexpr int SZ = N * N;

using Board = array<uint8_t, SZ>;

static inline int id(int r, int c) { return r * N + c; }

static Board tilt(const Board& b, int dir) {
    Board out{};
    out.fill(0);

    if (dir == 0) { // F: up (row--)
        for (int c = 0; c < N; c++) {
            int wr = 0;
            for (int r = 0; r < N; r++) {
                uint8_t v = b[id(r, c)];
                if (v) out[id(wr++, c)] = v;
            }
        }
    } else if (dir == 1) { // B: down (row++)
        for (int c = 0; c < N; c++) {
            int wr = N - 1;
            for (int r = N - 1; r >= 0; r--) {
                uint8_t v = b[id(r, c)];
                if (v) out[id(wr--, c)] = v;
            }
        }
    } else if (dir == 2) { // L: left (col--)
        for (int r = 0; r < N; r++) {
            int wc = 0;
            for (int c = 0; c < N; c++) {
                uint8_t v = b[id(r, c)];
                if (v) out[id(r, wc++)] = v;
            }
        }
    } else { // R: right (col++)
        for (int r = 0; r < N; r++) {
            int wc = N - 1;
            for (int c = N - 1; c >= 0; c--) {
                uint8_t v = b[id(r, c)];
                if (v) out[id(r, wc--)] = v;
            }
        }
    }
    return out;
}

static inline long long evalBoard(const Board& b) {
    // heuristic: (sum of component sizes^2)*1000 + adjacencyCount
    bool vis[SZ] = {};
    long long compSq = 0;

    int q[SZ];
    for (int i = 0; i < SZ; i++) {
        if (b[i] == 0 || vis[i]) continue;
        uint8_t col = b[i];
        int qs = 0, qe = 0;
        q[qe++] = i;
        vis[i] = true;
        int cnt = 0;
        while (qs < qe) {
            int v = q[qs++];
            cnt++;
            int r = v / N, c = v % N;
            if (r > 0) {
                int u = v - N;
                if (!vis[u] && b[u] == col) { vis[u] = true; q[qe++] = u; }
            }
            if (r + 1 < N) {
                int u = v + N;
                if (!vis[u] && b[u] == col) { vis[u] = true; q[qe++] = u; }
            }
            if (c > 0) {
                int u = v - 1;
                if (!vis[u] && b[u] == col) { vis[u] = true; q[qe++] = u; }
            }
            if (c + 1 < N) {
                int u = v + 1;
                if (!vis[u] && b[u] == col) { vis[u] = true; q[qe++] = u; }
            }
        }
        compSq += 1LL * cnt * cnt;
    }

    long long adj = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            uint8_t v = b[id(r, c)];
            if (!v) continue;
            if (c + 1 < N && b[id(r, c + 1)] == v) adj++;
            if (r + 1 < N && b[id(r + 1, c)] == v) adj++;
        }
    }
    return compSq * 1000 + adj;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    array<int, 100> f{};
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    Board cur{};
    cur.fill(0);

    const char dirs[4] = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) break;

        // place t-th candy into p-th empty cell (row-major)
        int cnt = 0;
        int pos = -1;
        for (int i = 0; i < SZ; i++) {
            if (cur[i] == 0) {
                cnt++;
                if (cnt == p) { pos = i; break; }
            }
        }
        if (pos == -1) pos = 0; // should not happen
        cur[pos] = (uint8_t)f[t];

        int bestDir = 0;
        long long bestValue = LLONG_MIN;
        long long bestNow = LLONG_MIN;

        for (int d1 = 0; d1 < 4; d1++) {
            Board b1 = tilt(cur, d1);
            long long score1 = evalBoard(b1);

            long long value;
            if (t == 99) {
                value = score1;
            } else {
                int nextFlavor = f[t + 1];
                int emptyCount = 0;
                int empties[SZ];
                for (int i = 0; i < SZ; i++) if (b1[i] == 0) empties[emptyCount++] = i;

                long long sumBest = 0;
                for (int ei = 0; ei < emptyCount; ei++) {
                    Board b2 = b1;
                    b2[empties[ei]] = (uint8_t)nextFlavor;

                    long long best2 = LLONG_MIN;
                    for (int d2 = 0; d2 < 4; d2++) {
                        Board b3 = tilt(b2, d2);
                        long long sc = evalBoard(b3);
                        if (sc > best2) best2 = sc;
                    }
                    sumBest += best2;
                }

                long long expected = (emptyCount ? (sumBest / emptyCount) : score1);
                // value = score1 + 0.05 * expected  ==> scaled by 20: 20*score1 + expected
                value = score1 * 20 + expected;
            }

            if (value > bestValue || (value == bestValue && score1 > bestNow)) {
                bestValue = value;
                bestNow = score1;
                bestDir = d1;
            }
        }

        cout << dirs[bestDir] << '\n' << flush;
        cur = tilt(cur, bestDir);
    }

    return 0;
}