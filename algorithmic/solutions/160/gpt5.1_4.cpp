#include <bits/stdc++.h>
using namespace std;

static const int H = 10;
static const int W = 10;
using Grid = array<array<int, W>, H>;

void tilt(char dir, Grid &g) {
    if (dir == 'F') {
        for (int c = 0; c < W; c++) {
            int tmp[H];
            int k = 0;
            for (int r = 0; r < H; r++) {
                if (g[r][c] != 0) tmp[k++] = g[r][c];
            }
            for (int r = 0; r < H; r++) {
                if (r < k) g[r][c] = tmp[r];
                else g[r][c] = 0;
            }
        }
    } else if (dir == 'B') {
        for (int c = 0; c < W; c++) {
            int tmp[H];
            int k = 0;
            for (int r = 0; r < H; r++) {
                if (g[r][c] != 0) tmp[k++] = g[r][c];
            }
            int start = H - k;
            for (int r = 0; r < H; r++) {
                if (r < start) g[r][c] = 0;
                else g[r][c] = tmp[r - start];
            }
        }
    } else if (dir == 'L') {
        for (int r = 0; r < H; r++) {
            int tmp[W];
            int k = 0;
            for (int c = 0; c < W; c++) {
                if (g[r][c] != 0) tmp[k++] = g[r][c];
            }
            for (int c = 0; c < W; c++) {
                if (c < k) g[r][c] = tmp[c];
                else g[r][c] = 0;
            }
        }
    } else if (dir == 'R') {
        for (int r = 0; r < H; r++) {
            int tmp[W];
            int k = 0;
            for (int c = 0; c < W; c++) {
                if (g[r][c] != 0) tmp[k++] = g[r][c];
            }
            int start = W - k;
            for (int c = 0; c < W; c++) {
                if (c < start) g[r][c] = 0;
                else g[r][c] = tmp[c - start];
            }
        }
    }
}

long long computeScore(const Grid &g) {
    const int N = H * W;
    int par[N];
    int sz[N];
    for (int i = 0; i < N; i++) {
        par[i] = i;
        sz[i] = 1;
    }
    auto find = [&](int x) {
        int r = x;
        while (par[r] != r) r = par[r];
        while (par[x] != x) {
            int p = par[x];
            par[x] = r;
            x = p;
        }
        return r;
    };
    auto unite = [&](int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return;
        if (sz[a] < sz[b]) swap(a, b);
        par[b] = a;
        sz[a] += sz[b];
    };

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            if (g[r][c] == 0) continue;
            int id = r * W + c;
            if (c + 1 < W && g[r][c + 1] == g[r][c]) {
                int id2 = r * W + (c + 1);
                unite(id, id2);
            }
            if (r + 1 < H && g[r + 1][c] == g[r][c]) {
                int id2 = (r + 1) * W + c;
                unite(id, id2);
            }
        }
    }

    bool seen[N];
    memset(seen, 0, sizeof(seen));
    long long ans = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            if (g[r][c] == 0) continue;
            int id = r * W + c;
            int root = find(id);
            if (!seen[root]) {
                seen[root] = true;
                ans += 1LL * sz[root] * sz[root];
            }
        }
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> flavor(100);
    for (int i = 0; i < 100; i++) {
        if (!(cin >> flavor[i])) return 0;
    }

    Grid board;
    for (int r = 0; r < H; r++)
        for (int c = 0; c < W; c++)
            board[r][c] = 0;

    const char dirs[4] = {'F', 'B', 'L', 'R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) return 0;

        int cnt = 0;
        int cr = -1, cc = -1;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                if (board[r][c] == 0) {
                    cnt++;
                    if (cnt == p) {
                        cr = r;
                        cc = c;
                        break;
                    }
                }
            }
            if (cr != -1) break;
        }
        if (cr == -1) {
            cr = 0;
            cc = 0;
        }

        board[cr][cc] = flavor[t];

        char bestDir = 'F';
        long long bestScore = -1;
        for (int di = 0; di < 4; di++) {
            Grid tmp = board;
            tilt(dirs[di], tmp);
            long long s = computeScore(tmp);
            if (s > bestScore) {
                bestScore = s;
                bestDir = dirs[di];
            }
        }

        cout << bestDir << '\n' << flush;
        tilt(bestDir, board);
    }

    return 0;
}