#include <bits/stdc++.h>
using namespace std;

static const int N = 10;

struct State {
    int g[N][N];
};

static inline State tilt(const State &s, char dir) {
    State t{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) t.g[r][c] = 0;

    if (dir == 'F') { // up
        for (int c = 0; c < N; c++) {
            int w = 0;
            for (int r = 0; r < N; r++) if (s.g[r][c] != 0) t.g[w++][c] = s.g[r][c];
        }
    } else if (dir == 'B') { // down
        for (int c = 0; c < N; c++) {
            int w = N - 1;
            for (int r = N - 1; r >= 0; r--) if (s.g[r][c] != 0) t.g[w--][c] = s.g[r][c];
        }
    } else if (dir == 'L') { // left
        for (int r = 0; r < N; r++) {
            int w = 0;
            for (int c = 0; c < N; c++) if (s.g[r][c] != 0) t.g[r][w++] = s.g[r][c];
        }
    } else { // 'R' right
        for (int r = 0; r < N; r++) {
            int w = N - 1;
            for (int c = N - 1; c >= 0; c--) if (s.g[r][c] != 0) t.g[r][w--] = s.g[r][c];
        }
    }
    return t;
}

static inline long long compScore(const State &s) {
    bool vis[N][N]{};
    long long sumsq = 0;
    static const int dr[4] = {1, -1, 0, 0};
    static const int dc[4] = {0, 0, 1, -1};

    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) {
        if (s.g[r][c] == 0 || vis[r][c]) continue;
        int col = s.g[r][c];
        int cnt = 0;
        queue<pair<int,int>> q;
        vis[r][c] = true;
        q.push({r,c});
        while (!q.empty()) {
            auto [x,y] = q.front(); q.pop();
            cnt++;
            for (int k = 0; k < 4; k++) {
                int nx = x + dr[k], ny = y + dc[k];
                if (0 <= nx && nx < N && 0 <= ny && ny < N && !vis[nx][ny] && s.g[nx][ny] == col) {
                    vis[nx][ny] = true;
                    q.push({nx,ny});
                }
            }
        }
        sumsq += 1LL * cnt * cnt;
    }
    return sumsq;
}

static inline int adjScore(const State &s) {
    int adj = 0;
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) {
        int v = s.g[r][c];
        if (!v) continue;
        if (r + 1 < N && s.g[r + 1][c] == v) adj++;
        if (c + 1 < N && s.g[r][c + 1] == v) adj++;
    }
    return adj;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; i++) cin >> f[i];

    int cnt[4] = {0,0,0,0};
    for (int x : f) cnt[x]++;

    // Assign flavors to three corners (largest groups first) for a weak bias term.
    vector<int> flavors = {1,2,3};
    sort(flavors.begin(), flavors.end(), [&](int a, int b){ return cnt[a] > cnt[b]; });

    pair<int,int> corner[4];
    corner[flavors[0]] = {0, 0};
    corner[flavors[1]] = {0, 9};
    corner[flavors[2]] = {9, 0};

    State cur{};
    for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) cur.g[r][c] = 0;

    char prev = 'F';
    const char dirs[4] = {'F','B','L','R'};

    for (int t = 0; t < 100; t++) {
        int p;
        if (!(cin >> p)) break;

        // Place candy at p-th empty cell (row-major).
        int k = p;
        int pr = -1, pc = -1;
        for (int r = 0; r < N && pr == -1; r++) {
            for (int c = 0; c < N; c++) {
                if (cur.g[r][c] == 0) {
                    k--;
                    if (k == 0) { pr = r; pc = c; break; }
                }
            }
        }
        if (pr != -1) cur.g[pr][pc] = f[t];

        // Choose best tilt.
        long long bestH = LLONG_MIN;
        char bestD = 'F';
        for (char d : dirs) {
            State nxt = tilt(cur, d);

            long long cs = compScore(nxt);
            int as = adjScore(nxt);

            long long distSum = 0;
            for (int r = 0; r < N; r++) for (int c = 0; c < N; c++) {
                int v = nxt.g[r][c];
                if (!v) continue;
                auto [tr, tc] = corner[v];
                distSum += llabs(r - tr) + llabs(c - tc);
            }
            long long region = -distSum;

            long long H = cs * 1000000LL + 1000LL * as + 10LL * region;
            if (d == prev) H += 5;

            if (H > bestH) {
                bestH = H;
                bestD = d;
            }
        }

        // Apply chosen tilt and output.
        cur = tilt(cur, bestD);
        prev = bestD;

        cout << bestD << "\n" << flush;
    }

    return 0;
}