#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(int x1, int y1, int x2, int y2) {
    // 0-based -> 1-based for interaction
    cout << "? " << x1 + 1 << " " << y1 + 1 << " " << x2 + 1 << " " << y2 + 1 << "\n";
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static int askEqDist2(int x1, int y1, int x2, int y2) {
    // Ensure (x1,y1) <= (x2,y2) component-wise (comparability is guaranteed by caller)
    if (x1 > x2 || y1 > y2) {
        swap(x1, x2);
        swap(y1, y2);
    }
    return ask(x1, y1, x2, y2); // for dist=2, reply is 1 iff endpoints equal
}

static bool simulateQuery(const vector<string>& g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1;
    int dy = y2 - y1;
    int d = dx + dy;

    if (dx < 0 || dy < 0) return false;
    if (g[x1][y1] != g[x2][y2]) return false; // palindrome endpoints must match

    int tmax = d / 2;
    vector<bitset<50>> dp(dx + 1), ndp(dx + 1);
    dp[0].set(0);

    for (int t = 0; t < tmax; ++t) {
        for (int i = 0; i <= dx; ++i) {
            bitset<50> res = dp[i] | (dp[i] << 1);
            if (i > 0) res |= dp[i - 1] | (dp[i - 1] << 1);
            ndp[i] = res;
        }

        int s = t + 1; // next step count from both ends
        for (int i = 0; i <= dx; ++i) {
            int pyOff = s - i;
            if (pyOff < 0 || pyOff > dy) {
                ndp[i].reset();
                continue;
            }

            int px = x1 + i;
            int py = y1 + pyOff;
            char pv = g[px][py];

            int jmin = 0;
            jmin = max(jmin, s - dy);             // ensure (s - j) <= dy
            jmin = max(jmin, 2 * s - dy - i);     // ensure i + j >= 2s - dy
            int jmax = dx;
            jmax = min(jmax, s);                  // ensure j <= s
            jmax = min(jmax, dx - i);             // ensure i + j <= dx
            if (jmin > jmax) {
                ndp[i].reset();
                continue;
            }

            bitset<50> mask;
            int baseY = y2 - s;
            for (int j = jmin; j <= jmax; ++j) {
                int qx = x2 - j;
                int qy = baseY + j;
                if (pv == g[qx][qy]) mask.set(j);
            }
            ndp[i] &= mask;
        }

        dp.swap(ndp);
    }

    if (d % 2 == 0) {
        // must meet at same cell => i + j == dx
        for (int i = 0; i <= dx; ++i) {
            int j = dx - i;
            if (0 <= j && j <= dx && dp[i].test(j)) return true;
        }
        return false;
    } else {
        // remaining distance is 1; any valid state works
        for (int i = 0; i <= dx; ++i)
            if (dp[i].any()) return true;
        return false;
    }
}

struct DiffQuery {
    int x1, y1, x2, y2;
    int predA, predB;
};

static optional<DiffQuery> findDistinguishingQuery(const vector<string>& A, const vector<string>& B) {
    auto tryPair = [&](int x1, int y1, int x2, int y2) -> optional<DiffQuery> {
        if (x1 > x2 || y1 > y2) return nullopt;
        int d = (x2 - x1) + (y2 - y1);
        if (d < 2) return nullopt;
        if (((x1 + y1) & 1) == ((x2 + y2) & 1)) return nullopt; // need opposite parity to differ
        bool pa = simulateQuery(A, x1, y1, x2, y2);
        bool pb = simulateQuery(B, x1, y1, x2, y2);
        if (pa != pb) return DiffQuery{x1, y1, x2, y2, (int)pa, (int)pb};
        return nullopt;
    };

    int limD = min(2 * n - 3, 21);
    for (int D = 3; D <= limD; D += 2) {
        for (int x1 = 0; x1 < n; ++x1) {
            for (int y1 = 0; y1 < n; ++y1) {
                for (int dx = 0; dx <= D; ++dx) {
                    int dy = D - dx;
                    int x2 = x1 + dx, y2 = y1 + dy;
                    if (x2 >= n || y2 >= n) continue;
                    auto r = tryPair(x1, y1, x2, y2);
                    if (r) return r;
                }
            }
        }
    }

    // Try some long-ish structured queries from (0,0)
    for (int k = 2; k < n; ++k) {
        if (k - 1 >= 0) {
            auto r1 = tryPair(0, 0, k, k - 1);
            if (r1) return r1;
            auto r2 = tryPair(0, 0, k - 1, k);
            if (r2) return r2;
        }
    }

    // Corner-related candidates
    vector<array<int,4>> cand = {
        {0, 0, n - 1, n - 2},
        {0, 0, n - 2, n - 1},
        {0, 1, n - 1, n - 1},
        {1, 0, n - 1, n - 1},
        {0, 0, n - 1, n - 3},
        {0, 0, n - 3, n - 1},
    };
    for (auto p : cand) {
        int x1=p[0], y1=p[1], x2=p[2], y2=p[3];
        if (0 <= x1 && x1 < n && 0 <= y1 && y1 < n && 0 <= x2 && x2 < n && 0 <= y2 && y2 < n) {
            auto r = tryPair(x1, y1, x2, y2);
            if (r) return r;
        }
    }

    // Exhaustive endpoints from (0,0) (usually not needed)
    for (int x2 = 0; x2 < n; ++x2) {
        for (int y2 = 0; y2 < n; ++y2) {
            auto r = tryPair(0, 0, x2, y2);
            if (r) return r;
        }
    }

    // Try some additional starts (even parity) if needed
    for (int s = 0; s < n; ++s) {
        int x1 = 0, y1 = s;
        if (((x1 + y1) & 1) != 0) continue;
        for (int x2 = x1; x2 < n; ++x2) {
            for (int y2 = y1; y2 < n; ++y2) {
                auto r = tryPair(x1, y1, x2, y2);
                if (r) return r;
            }
        }
    }

    return nullopt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    vector<vector<int>> evenVal(n, vector<int>(n, -1));
    vector<vector<int>> oddRel(n, vector<int>(n, -1));

    const int dirs[6][2] = {
        { 2,  0},
        { 0,  2},
        { 1,  1},
        {-2,  0},
        { 0, -2},
        {-1, -1}
    };

    // BFS for even parity absolute values
    {
        queue<pair<int,int>> q;
        evenVal[0][0] = 1;
        q.push({0,0});

        while (!q.empty()) {
            auto [x,y] = q.front();
            q.pop();

            for (auto &dxy : dirs) {
                int nx = x + dxy[0], ny = y + dxy[1];
                if (nx < 0 || nx >= n || ny < 0 || ny >= n) continue;
                if (((nx + ny) & 1) != 0) continue; // even parity only
                if (evenVal[nx][ny] != -1) continue;

                int eq = askEqDist2(x, y, nx, ny);
                evenVal[nx][ny] = evenVal[x][y] ^ (eq ? 0 : 1);
                q.push({nx, ny});
            }
        }
    }

    // BFS for odd parity relative values (xor with root (0,1))
    {
        queue<pair<int,int>> q;
        oddRel[0][1] = 0;
        q.push({0,1});

        while (!q.empty()) {
            auto [x,y] = q.front();
            q.pop();

            for (auto &dxy : dirs) {
                int nx = x + dxy[0], ny = y + dxy[1];
                if (nx < 0 || nx >= n || ny < 0 || ny >= n) continue;
                if (((nx + ny) & 1) != 1) continue; // odd parity only
                if (oddRel[nx][ny] != -1) continue;

                int eq = askEqDist2(x, y, nx, ny);
                oddRel[nx][ny] = oddRel[x][y] ^ (eq ? 0 : 1);
                q.push({nx, ny});
            }
        }
    }

    // Build candidate grids
    vector<string> A(n, string(n, '0')), B(n, string(n, '0'));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (((i + j) & 1) == 0) {
                int v = evenVal[i][j];
                if (v < 0) v = 0;
                A[i][j] = B[i][j] = char('0' + v);
            } else {
                int r = oddRel[i][j];
                if (r < 0) r = 0;
                A[i][j] = char('0' + r);
                B[i][j] = char('0' + (r ^ 1));
            }
        }
    }

    // Find a distinguishing query and ask it
    auto diff = findDistinguishingQuery(A, B);
    vector<string> ans = A;
    if (diff) {
        int real = ask(diff->x1, diff->y1, diff->x2, diff->y2);
        if (real == diff->predA) ans = A;
        else ans = B;
    } else {
        // Should not happen in solvable instances
        ans = A;
    }

    cout << "!\n";
    for (int i = 0; i < n; ++i) cout << ans[i] << "\n";
    cout.flush();
    return 0;
}