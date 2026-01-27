#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> a;

// Ask the interactive judge if there exists a palindromic path between (x1,y1) and (x2,y2)
int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

// Get value at (i,j) assuming odd cells are flipped by s (s in {0,1})
inline int getVal(int i, int j, int s) {
    int v = a[i][j];
    if (((i + j) & 1) == 1) v ^= s;
    return v;
}

// Check if there exists a palindromic path between (x1,y1) and (x2,y2) using current grid with odd flipped by s
bool existsPal(int x1, int y1, int x2, int y2, int s) {
    int d = (x2 - x1) + (y2 - y1);
    if (getVal(x1, y1, s) != getVal(x2, y2, s)) return false;

    int W = x2 - x1 + 1;
    int H = y2 - y1 + 1;

    // 4D boolean arrays for current and next states
    static bool cur[55][55][55][55];
    static bool nxt[55][55][55][55];

    for (int i1 = 0; i1 < W; ++i1)
        for (int j1 = 0; j1 < H; ++j1)
            for (int i2 = 0; i2 < W; ++i2)
                for (int j2 = 0; j2 < H; ++j2)
                    cur[i1][j1][i2][j2] = false;

    cur[0][0][W - 1][H - 1] = true;

    int steps = d / 2; // number of expansions

    for (int step = 0; step < steps; ++step) {
        for (int i1 = 0; i1 < W; ++i1)
            for (int j1 = 0; j1 < H; ++j1)
                for (int i2 = 0; i2 < W; ++i2)
                    for (int j2 = 0; j2 < H; ++j2)
                        nxt[i1][j1][i2][j2] = false;

        for (int i1 = 0; i1 < W; ++i1) {
            for (int j1 = 0; j1 < H; ++j1) {
                for (int i2 = 0; i2 < W; ++i2) {
                    for (int j2 = 0; j2 < H; ++j2) {
                        if (!cur[i1][j1][i2][j2]) continue;

                        // From left pointer: move right or down
                        int ni1s[2] = {i1 + 1, i1};
                        int nj1s[2] = {j1, j1 + 1};

                        // From right pointer: move left or up
                        int ni2s[2] = {i2 - 1, i2};
                        int nj2s[2] = {j2, j2 - 1};

                        for (int t1 = 0; t1 < 2; ++t1) {
                            int ni1 = ni1s[t1], nj1 = nj1s[t1];
                            if (ni1 >= W || nj1 >= H) continue;
                            for (int t2 = 0; t2 < 2; ++t2) {
                                int ni2 = ni2s[t2], nj2 = nj2s[t2];
                                if (ni2 < 0 || nj2 < 0) continue;
                                if (ni1 > ni2 || nj1 > nj2) continue;

                                int xi1 = x1 + ni1, yj1 = y1 + nj1;
                                int xi2 = x1 + ni2, yj2 = y1 + nj2;
                                if (getVal(xi1, yj1, s) != getVal(xi2, yj2, s)) continue;

                                nxt[ni1][nj1][ni2][nj2] = true;
                            }
                        }
                    }
                }
            }
        }

        for (int i1 = 0; i1 < W; ++i1)
            for (int j1 = 0; j1 < H; ++j1)
                for (int i2 = 0; i2 < W; ++i2)
                    for (int j2 = 0; j2 < H; ++j2)
                        cur[i1][j1][i2][j2] = nxt[i1][j1][i2][j2];
    }

    if (d % 2 == 0) {
        // Need to meet at same cell
        for (int i1 = 0; i1 < W; ++i1)
            for (int j1 = 0; j1 < H; ++j1)
                if (cur[i1][j1][i1][j1]) return true;
        return false;
    } else {
        // Need to be adjacent
        for (int i1 = 0; i1 < W; ++i1) {
            for (int j1 = 0; j1 < H; ++j1) {
                for (int i2 = i1; i2 < W; ++i2) {
                    for (int j2 = j1; j2 < H; ++j2) {
                        if (!cur[i1][j1][i2][j2]) continue;
                        if ((i2 - i1) + (j2 - j1) == 1) return true;
                    }
                }
            }
        }
        return false;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    a.assign(n + 1, vector<int>(n + 1, -1));
    a[1][1] = 1;
    a[n][n] = 0;

    // BFS to fill even parity cells using distance 2 queries
    queue<pair<int,int>> q;
    q.push({1, 1});
    vector<vector<int>> vis_even(n + 1, vector<int>(n + 1, 0));
    vis_even[1][1] = 1;
    int dx[3] = {2, 0, 1};
    int dy[3] = {0, 2, 1};

    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int dir = 0; dir < 3; ++dir) {
            int nx = x + dx[dir], ny = y + dy[dir];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (((nx + ny) & 1) != 0) continue; // ensure same parity (even)
            if (vis_even[nx][ny]) continue;
            int res = ask(x, y, nx, ny);
            a[nx][ny] = a[x][y] ^ (1 - res);
            vis_even[nx][ny] = 1;
            q.push({nx, ny});
        }
    }

    // BFS to fill odd parity cells; start from (1,2) if exists
    if (n >= 2) {
        int sx = 1, sy = 2;
        a[sx][sy] = 0; // arbitrary initial guess for odd parity group
        queue<pair<int,int>> q2;
        q2.push({sx, sy});
        vector<vector<int>> vis_odd(n + 1, vector<int>(n + 1, 0));
        vis_odd[sx][sy] = 1;

        while (!q2.empty()) {
            auto [x, y] = q2.front(); q2.pop();
            for (int dir = 0; dir < 3; ++dir) {
                int nx = x + dx[dir], ny = y + dy[dir];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if (((nx + ny) & 1) != 1) continue; // same odd parity
                if (vis_odd[nx][ny]) continue;
                int res = ask(x, y, nx, ny);
                a[nx][ny] = a[x][y] ^ (1 - res);
                vis_odd[nx][ny] = 1;
                q2.push({nx, ny});
            }
        }
    }

    // Find a pair (x1,y1)-(x2,y2) with odd distance where predictions differ for s=0 and s=1
    int X1 = -1, Y1 = -1, X2 = -1, Y2 = -1;
    bool found = false;

    int maxd = min(2 * n - 2, 9); // search up to distance 9 (odd distances)
    for (int d = 3; d <= maxd && !found; d += 2) {
        for (int x1 = 1; x1 <= n && !found; ++x1) {
            for (int y1 = 1; y1 <= n && !found; ++y1) {
                int s1 = x1 + y1;
                int s2min = s1 + d;
                for (int dx2 = 0; dx2 <= d; ++dx2) {
                    int dy2 = d - dx2;
                    int x2 = x1 + dx2;
                    int y2 = y1 + dy2;
                    if (x2 < 1 || x2 > n || y2 < 1 || y2 > n) continue;
                    if ((x1 + y1 + 2) > (x2 + y2)) continue;
                    // Only consider different parity endpoints
                    if (((x1 + y1) & 1) == ((x2 + y2) & 1)) continue;
                    bool p0 = existsPal(x1, y1, x2, y2, 0);
                    bool p1 = existsPal(x1, y1, x2, y2, 1);
                    if (p0 != p1) {
                        X1 = x1; Y1 = y1; X2 = x2; Y2 = y2;
                        found = true;
                        break;
                    }
                }
            }
        }
    }

    // If not found in small distances, increase search radius cautiously
    if (!found) {
        int maxd2 = min(2 * n - 2, 15);
        for (int d = 11; d <= maxd2 && !found; d += 2) {
            for (int x1 = 1; x1 <= n && !found; ++x1) {
                for (int y1 = 1; y1 <= n && !found; ++y1) {
                    for (int dx2 = 0; dx2 <= d; ++dx2) {
                        int dy2 = d - dx2;
                        int x2 = x1 + dx2;
                        int y2 = y1 + dy2;
                        if (x2 < 1 || x2 > n || y2 < 1 || y2 > n) continue;
                        if ((x1 + y1 + 2) > (x2 + y2)) continue;
                        if (((x1 + y1) & 1) == ((x2 + y2) & 1)) continue;
                        bool p0 = existsPal(x1, y1, x2, y2, 0);
                        bool p1 = existsPal(x1, y1, x2, y2, 1);
                        if (p0 != p1) {
                            X1 = x1; Y1 = y1; X2 = x2; Y2 = y2;
                            found = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    int s = 0; // orientation: 0 if our odd guess was correct, 1 if we need to flip odd cells
    if (found) {
        int realAns = ask(X1, Y1, X2, Y2);
        bool p0 = existsPal(X1, Y1, X2, Y2, 0);
        // If real answer matches p0, s=0; else s=1
        s = (realAns == (int)p0) ? 0 : 1;
    } else {
        // Fallback: if no distinguishing pair found (shouldn't happen), assume s=0
        s = 0;
    }

    // Apply orientation
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (((i + j) & 1) == 1) a[i][j] ^= s;
        }
    }

    // Output final grid
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << a[i][j];
        }
        cout << '\n';
    }
    cout.flush();
    return 0;
}