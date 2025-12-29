#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 10;

using Grid = array<array<int, N>, N>;

static inline Grid tilt_grid(const Grid& g, char dir) {
    Grid ng{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) ng[r][c] = 0;

    if (dir == 'L') {
        for (int r = 0; r < N; r++) {
            int w = 0;
            for (int c = 0; c < N; c++) if (g[r][c] != 0) ng[r][w++] = g[r][c];
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; r++) {
            int w = N - 1;
            for (int c = N - 1; c >= 0; c--) if (g[r][c] != 0) ng[r][w--] = g[r][c];
        }
    } else if (dir == 'F') { // up
        for (int c = 0; c < N; c++) {
            int w = 0;
            for (int r = 0; r < N; r++) if (g[r][c] != 0) ng[w++][c] = g[r][c];
        }
    } else if (dir == 'B') { // down
        for (int c = 0; c < N; c++) {
            int w = N - 1;
            for (int r = N - 1; r >= 0; r--) if (g[r][c] != 0) ng[w--][c] = g[r][c];
        }
    }
    return ng;
}

static inline void place_by_p(Grid& g, int flavor, int p) {
    int cnt = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (g[r][c] == 0) {
                cnt++;
                if (cnt == p) {
                    g[r][c] = flavor;
                    return;
                }
            }
        }
    }
}

struct Eval {
    long long H;
    long long compSq;
    int sameAdj;
    int diffAdj;
    int areaSum;
};

static inline Eval evaluate_grid(const Grid& g, int t) {
    bool vis[N][N]{};
    long long compSq = 0;

    static int dr[4] = {1, -1, 0, 0};
    static int dc[4] = {0, 0, 1, -1};

    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (g[r][c] == 0 || vis[r][c]) continue;
            int col = g[r][c];
            int sz = 0;
            queue<pair<int,int>> q;
            vis[r][c] = true;
            q.push({r,c});
            while (!q.empty()) {
                auto [cr, cc] = q.front(); q.pop();
                sz++;
                for (int k = 0; k < 4; k++) {
                    int nr = cr + dr[k], nc = cc + dc[k];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (vis[nr][nc]) continue;
                    if (g[nr][nc] != col) continue;
                    vis[nr][nc] = true;
                    q.push({nr,nc});
                }
            }
            compSq += 1LL * sz * sz;
        }
    }

    int sameAdj = 0, diffAdj = 0;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            if (g[r][c] == 0) continue;
            if (c + 1 < N && g[r][c + 1] != 0) {
                if (g[r][c + 1] == g[r][c]) sameAdj++;
                else diffAdj++;
            }
            if (r + 1 < N && g[r + 1][c] != 0) {
                if (g[r + 1][c] == g[r][c]) sameAdj++;
                else diffAdj++;
            }
        }
    }

    int areaSum = 0;
    for (int f = 1; f <= 3; f++) {
        int minr = N, minc = N, maxr = -1, maxc = -1;
        for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) if (g[r][c] == f) {
            minr = min(minr, r);
            minc = min(minc, c);
            maxr = max(maxr, r);
            maxc = max(maxc, c);
        }
        if (maxr != -1) areaSum += (maxr - minr + 1) * (maxc - minc + 1);
    }

    long long wA = 200000LL + 5000LL * t;   // emphasize component growth later
    long long wS = 4000LL;                  // reward same-adjacent
    long long wD = 20000LL;                 // penalize different-adjacent
    long long wArea = 200LL;                // penalize spread

    long long H = compSq * wA + 1LL * sameAdj * wS - 1LL * diffAdj * wD - 1LL * areaSum * wArea;

    return {H, compSq, sameAdj, diffAdj, areaSum};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(101);
    for (int i = 1; i <= 100; i++) {
        if (!(cin >> f[i])) return 0;
    }

    Grid g{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) g[r][c] = 0;

    const array<char, 4> dirs = {'F', 'B', 'L', 'R'};

    for (int t = 1; t <= 100; t++) {
        int p;
        if (!(cin >> p)) break;

        place_by_p(g, f[t], p);

        if (t == 100) break;

        char bestDir = 'F';
        Eval bestEval{LLONG_MIN, 0, 0, 0, 0};

        for (char d : dirs) {
            Grid ng = tilt_grid(g, d);
            Eval e = evaluate_grid(ng, t);
            if (e.H > bestEval.H ||
                (e.H == bestEval.H && e.compSq > bestEval.compSq) ||
                (e.H == bestEval.H && e.compSq == bestEval.compSq && e.diffAdj < bestEval.diffAdj)) {
                bestEval = e;
                bestDir = d;
            }
        }

        g = tilt_grid(g, bestDir);
        cout << bestDir << '\n' << flush;
    }

    return 0;
}