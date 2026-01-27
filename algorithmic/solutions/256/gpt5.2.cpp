#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 + 1 << " " << y1 + 1 << " " << x2 + 1 << " " << y2 + 1 << "\n" << flush;
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static void bfs_parity(vector<vector<int>> &a, int parity, const vector<pair<int,int>> &seeds) {
    static const int dxs[] = { 2, -2, 0, 0, 1, -1 };
    static const int dys[] = { 0, 0, 2, -2, 1, -1 };

    queue<pair<int,int>> q;
    for (auto [sx, sy] : seeds) {
        q.push({sx, sy});
    }

    auto inb = [&](int x, int y) {
        return 0 <= x && x < n && 0 <= y && y < n;
    };

    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int t = 0; t < 6; t++) {
            int nx = x + dxs[t], ny = y + dys[t];
            if (!inb(nx, ny)) continue;
            if (((nx + ny) & 1) != parity) continue;
            if (a[nx][ny] != -1) continue;

            int x1 = x, y1 = y, x2 = nx, y2 = ny;
            if (!(x1 <= x2 && y1 <= y2)) {
                swap(x1, x2);
                swap(y1, y2);
            }
            int r = ask(x1, y1, x2, y2); // 1 iff values equal
            a[nx][ny] = a[x][y] ^ (r == 0);
            q.push({nx, ny});
        }
    }
}

static bool pal_exists_enumerate(const vector<vector<uint8_t>> &g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;
    if (d < 2) return false;

    int vals[32];
    vals[0] = g[x1][y1];

    function<bool(int,int,int,int,int)> dfs = [&](int x, int y, int remD, int remR, int len) -> bool {
        if (remD == 0 && remR == 0) {
            for (int i = 0; i < len / 2; i++) {
                if (vals[i] != vals[len - 1 - i]) return false;
            }
            return true;
        }
        if (remD > 0) {
            vals[len] = g[x + 1][y];
            if (dfs(x + 1, y, remD - 1, remR, len + 1)) return true;
        }
        if (remR > 0) {
            vals[len] = g[x][y + 1];
            if (dfs(x, y + 0, remD, remR - 1, len + 1)) return true;
        }
        return false;
    };

    return dfs(x1, y1, dx, dy, 1);
}

static bool pal_exists_dp(const vector<vector<uint8_t>> &g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;
    if (d < 2) return false;
    if (g[x1][y1] != g[x2][y2]) return false;

    int mid = d / 2;
    static uint8_t dp[50][50], ndp[50][50];
    memset(dp, 0, sizeof(dp));
    dp[x1][x2] = 1;

    for (int k = 0; k < mid; k++) {
        memset(ndp, 0, sizeof(ndp));
        int r1_lo = x1, r1_hi = min(x2, x1 + k);
        int r2_lo = max(x1, x2 - k), r2_hi = x2;

        for (int r1 = r1_lo; r1 <= r1_hi; r1++) {
            for (int r2 = r2_lo; r2 <= r2_hi; r2++) {
                if (!dp[r1][r2]) continue;
                int c1 = y1 + (k - (r1 - x1));
                int c2 = y2 - (k - (x2 - r2));
                if (c1 < y1 || c1 > y2 || c2 < y1 || c2 > y2) continue;

                // move1: down or right
                for (int m1 = 0; m1 < 2; m1++) {
                    int r1n = r1 + (m1 == 0);
                    int c1n = c1 + (m1 == 1);
                    if (r1n < x1 || r1n > x2 || c1n < y1 || c1n > y2) continue;

                    // move2: up or left
                    for (int m2 = 0; m2 < 2; m2++) {
                        int r2n = r2 - (m2 == 0);
                        int c2n = c2 - (m2 == 1);
                        if (r2n < x1 || r2n > x2 || c2n < y1 || c2n > y2) continue;

                        if (r1n > r2n || c1n > c2n) continue;
                        if (g[r1n][c1n] != g[r2n][c2n]) continue;
                        ndp[r1n][r2n] = 1;
                    }
                }
            }
        }
        memcpy(dp, ndp, sizeof(dp));
    }

    int r1_lo = x1, r1_hi = min(x2, x1 + mid);
    int r2_lo = max(x1, x2 - mid), r2_hi = x2;
    bool odd_len = ((d + 1) & 1);

    for (int r1 = r1_lo; r1 <= r1_hi; r1++) {
        for (int r2 = r2_lo; r2 <= r2_hi; r2++) {
            if (!dp[r1][r2]) continue;
            int c1 = y1 + (mid - (r1 - x1));
            int c2 = y2 - (mid - (x2 - r2));
            if (c1 < y1 || c1 > y2 || c2 < y1 || c2 > y2) continue;

            if (odd_len) {
                if (r1 == r2 && c1 == c2) return true;
            } else {
                if (abs(r1 - r2) + abs(c1 - c2) == 1) return true;
            }
        }
    }
    return false;
}

struct PickedQuery {
    bool ok = false;
    int x1=0,y1=0,x2=0,y2=0;
    int p0=0,p1=0;
};

static PickedQuery find_distinguishing_query(const vector<vector<uint8_t>> &g0, const vector<vector<uint8_t>> &g1) {
    PickedQuery pq;

    auto check_q = [&](int x1,int y1,int x2,int y2, bool prefer_enum) -> bool {
        int d = (x2 - x1) + (y2 - y1);
        if (d < 2) return false;
        if (((x1 + y1) & 1) == ((x2 + y2) & 1)) return false;

        int p0, p1;
        if (prefer_enum && d <= 9) {
            p0 = pal_exists_enumerate(g0, x1, y1, x2, y2) ? 1 : 0;
            p1 = pal_exists_enumerate(g1, x1, y1, x2, y2) ? 1 : 0;
        } else {
            p0 = pal_exists_dp(g0, x1, y1, x2, y2) ? 1 : 0;
            p1 = pal_exists_dp(g1, x1, y1, x2, y2) ? 1 : 0;
        }
        if (p0 != p1) {
            pq.ok = true;
            pq.x1=x1; pq.y1=y1; pq.x2=x2; pq.y2=y2;
            pq.p0=p0; pq.p1=p1;
            return true;
        }
        return false;
    };

    // Stage A: odd distances up to 9 across the grid, enumerate
    for (int d : {3,5,7,9}) {
        for (int dx = 0; dx <= d; dx++) {
            int dy = d - dx;
            for (int x1 = 0; x1 + dx < n; x1++) {
                for (int y1 = 0; y1 + dy < n; y1++) {
                    int x2 = x1 + dx, y2 = y1 + dy;
                    if (check_q(x1,y1,x2,y2,true)) return pq;
                }
            }
        }
    }

    // Stage B: from (1,1) to any opposite parity cell
    for (int i = n - 1; i >= 0; i--) {
        for (int j = n - 1; j >= 0; j--) {
            if (((i + j) & 1) == 1 && (i + j) >= 2) {
                if (check_q(0,0,i,j,false)) return pq;
            }
        }
    }

    // Stage C: from any opposite parity cell to (n,n)
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int d = (n - 1 - i) + (n - 1 - j);
            if (((i + j) & 1) == 1 && d >= 2) {
                if (check_q(i,j,n-1,n-1,false)) return pq;
            }
        }
    }

    // Stage D: boundary-to-boundary families
    // (i,1) -> (n, j)
    for (int i = 0; i < n; i++) {
        for (int j = n - 1; j >= 0; j--) {
            int x1=i, y1=0, x2=n-1, y2=j;
            if (check_q(x1,y1,x2,y2,false)) return pq;
        }
    }
    // (1,i) -> (j, n)
    for (int i = 0; i < n; i++) {
        for (int j = n - 1; j >= 0; j--) {
            int x1=0, y1=i, x2=j, y2=n-1;
            if (check_q(x1,y1,x2,y2,false)) return pq;
        }
    }

    return pq; // may be !ok in degenerate scenario
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    vector<vector<int>> a(n, vector<int>(n, -1));

    a[0][0] = 1;
    a[n-1][n-1] = 0;

    // Fill even parity (i+j even), seed with both known corners
    bfs_parity(a, 0, {{0,0},{n-1,n-1}});

    // Fill odd parity (i+j odd), arbitrary seed
    a[0][1] = 0;
    bfs_parity(a, 1, {{0,1}});

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (a[i][j] == -1) {
                // Shouldn't happen; but safeguard with an arbitrary set and BFS continuation
                a[i][j] = 0;
                bfs_parity(a, (i + j) & 1, {{i,j}});
            }
        }
    }

    vector<vector<uint8_t>> g0(n, vector<uint8_t>(n, 0));
    vector<vector<uint8_t>> g1(n, vector<uint8_t>(n, 0));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            g0[i][j] = (uint8_t)a[i][j];
            g1[i][j] = (uint8_t)(a[i][j] ^ (((i + j) & 1) ? 1 : 0));
        }
    }

    vector<vector<uint8_t>> ansGrid = g0;
    PickedQuery pq = find_distinguishing_query(g0, g1);
    if (pq.ok) {
        int r = ask(pq.x1, pq.y1, pq.x2, pq.y2);
        if (r == pq.p0) ansGrid = g0;
        else ansGrid = g1;
    } else {
        // Fallback (should not be needed)
        ansGrid = g0;
    }

    cout << "!\n";
    for (int i = 0; i < n; i++) {
        string row;
        row.reserve(n);
        for (int j = 0; j < n; j++) row.push_back(char('0' + ansGrid[i][j]));
        cout << row << "\n";
    }
    cout << flush;
    return 0;
}