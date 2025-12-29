#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 10;

struct Board {
    array<int, N * N> a{}; // 0..3

    int& at(int r, int c) { return a[r * N + c]; }
    int  at(int r, int c) const { return a[r * N + c]; }
};

static inline Board tiltBoard(const Board& b, char dir) {
    Board nb;
    nb.a.fill(0);

    if (dir == 'L') {
        for (int r = 0; r < N; r++) {
            int w = 0;
            for (int c = 0; c < N; c++) {
                int v = b.at(r, c);
                if (v) nb.at(r, w++) = v;
            }
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; r++) {
            int w = N - 1;
            for (int c = N - 1; c >= 0; c--) {
                int v = b.at(r, c);
                if (v) nb.at(r, w--) = v;
            }
        }
    } else if (dir == 'F') { // towards row 0
        for (int c = 0; c < N; c++) {
            int w = 0;
            for (int r = 0; r < N; r++) {
                int v = b.at(r, c);
                if (v) nb.at(w++, c) = v;
            }
        }
    } else { // 'B' towards row N-1
        for (int c = 0; c < N; c++) {
            int w = N - 1;
            for (int r = N - 1; r >= 0; r--) {
                int v = b.at(r, c);
                if (v) nb.at(w--, c) = v;
            }
        }
    }
    return nb;
}

static inline long long evalBoard(const Board& b) {
    // Heuristic: primarily sum of component sizes^2 (same flavor, 4-neigh),
    // plus adjacency edges, minus number of components.
    array<char, N * N> vis{};
    vis.fill(0);

    long long compSq = 0;
    int compCnt = 0;

    static const int dr[4] = {1, -1, 0, 0};
    static const int dc[4] = {0, 0, 1, -1};

    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            int v = b.at(r, c);
            if (!v) continue;
            int id = r * N + c;
            if (vis[id]) continue;
            compCnt++;
            vis[id] = 1;
            int sz = 0;
            int qh = 0;
            array<int, N * N> q;
            q[qh++] = id;
            for (int qi = 0; qi < qh; qi++) {
                int cur = q[qi];
                int cr = cur / N, cc = cur % N;
                sz++;
                for (int k = 0; k < 4; k++) {
                    int nr = cr + dr[k], nc = cc + dc[k];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (b.at(nr, nc) != v) continue;
                    int nid = nr * N + nc;
                    if (vis[nid]) continue;
                    vis[nid] = 1;
                    q[qh++] = nid;
                }
            }
            compSq += 1LL * sz * sz;
        }
    }

    int adj = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            int v = b.at(r, c);
            if (!v) continue;
            if (c + 1 < N && b.at(r, c + 1) == v) adj++;
            if (r + 1 < N && b.at(r + 1, c) == v) adj++;
        }
    }

    // scale to prioritize compSq; avoid overflow
    return compSq * 1000000LL + 1000LL * adj - compCnt;
}

static inline pair<int,int> emptyCellByIndex(const Board& b, int p) {
    int cnt = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (b.at(r, c) == 0) {
                cnt++;
                if (cnt == p) return {r, c};
            }
        }
    }
    return {-1, -1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    array<int, 100> f{};
    for (int i = 0; i < 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    Board cur;
    cur.a.fill(0);

    const array<char, 4> dirs = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) break;

        auto [r, c] = emptyCellByIndex(cur, p);
        if (r < 0) break;
        cur.at(r, c) = f[t];

        char bestDir = 'L';
        long long bestVal = LLONG_MIN;
        Board bestBoard;

        for (char d : dirs) {
            Board nb = tiltBoard(cur, d);
            long long val = evalBoard(nb);
            if (val > bestVal) {
                bestVal = val;
                bestDir = d;
                bestBoard = nb;
            }
        }

        cur = bestBoard;

        cout << bestDir << '\n';
        cout.flush();
    }

    return 0;
}