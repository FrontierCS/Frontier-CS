#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> a;

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

inline int val_at(int i, int j, int flipOdd) {
    int v = a[i][j];
    if (((i + j) & 1) == 1) v ^= flipOdd;
    return v;
}

bool checkRect(int x1, int y1, int x2, int y2, int flipOdd) {
    int d = (x2 - x1) + (y2 - y1);
    int steps = d / 2;
    auto getv = [&](int i, int j) { return val_at(i, j, flipOdd); };

    if (getv(x1, y1) != getv(x2, y2)) return false;

    int w = x2 - x1 + 1;
    vector<vector<char>> cur(w, vector<char>(w, 0)), nxt(w, vector<char>(w, 0));
    cur[0][x2 - x1] = 1;

    int sumStart = x1 + y1;
    int sumEnd = x2 + y2;

    for (int s = 0; s < steps; ++s) {
        for (int i = 0; i < w; ++i) fill(nxt[i].begin(), nxt[i].end(), 0);
        for (int id1 = 0; id1 < w; ++id1) {
            for (int id2 = 0; id2 < w; ++id2) {
                if (!cur[id1][id2]) continue;
                int i1 = x1 + id1;
                int i2 = x1 + id2;
                int j1 = (sumStart + s) - i1;
                int j2 = (sumEnd - s) - i2;

                // Next moves from (i1,j1): (i1+1,j1), (i1,j1+1)
                // Next moves from (i2,j2): (i2-1,j2), (i2,j2-1)
                int ni1[2] = {i1 + 1, i1};
                int nj1[2] = {j1, j1 + 1};
                int ni2[2] = {i2 - 1, i2};
                int nj2[2] = {j2, j2 - 1};

                for (int t1 = 0; t1 < 2; ++t1) {
                    int ii1 = ni1[t1], jj1 = nj1[t1];
                    if (ii1 < x1 || ii1 > x2 || jj1 < y1 || jj1 > y2) continue;
                    for (int t2 = 0; t2 < 2; ++t2) {
                        int ii2 = ni2[t2], jj2 = nj2[t2];
                        if (ii2 < x1 || ii2 > x2 || jj2 < y1 || jj2 > y2) continue;
                        if (ii1 > ii2 || jj1 > jj2) continue;
                        if (getv(ii1, jj1) != getv(ii2, jj2)) continue;
                        nxt[ii1 - x1][ii2 - x1] = 1;
                    }
                }
            }
        }
        cur.swap(nxt);
    }
    for (int id1 = 0; id1 < w; ++id1) {
        for (int id2 = 0; id2 < w; ++id2) {
            if (!cur[id1][id2]) continue;
            int i1 = x1 + id1;
            int i2 = x1 + id2;
            int j1 = (sumStart + steps) - i1;
            int j2 = (sumEnd - steps) - i2;
            if (i1 < x1 || i1 > x2 || j1 < y1 || j1 > y2) continue;
            if (i2 < x1 || i2 > x2 || j2 < y1 || j2 > y2) continue;
            if (i1 > i2 || j1 > j2) continue;
            // If there's any valid state, palindromic path exists
            return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    a.assign(n + 1, vector<int>(n + 1, -1));

    // Known values
    a[1][1] = 1;
    a[n][n] = 0;

    // Directions for distance-2 same parity moves with monotone-compatible pairs:
    // We only use deltas where (dx, dy) are (±2,0), (0,±2), (±1,±1).
    const int DX[6] = {2, 0, 1, -2, 0, -1};
    const int DY[6] = {0, 2, 1, 0, -2, -1};

    // Fill even parity cells (starting from (1,1))
    {
        queue<pair<int,int>> q;
        q.push({1,1});
        vector<vector<char>> vis(n + 1, vector<char>(n + 1, 0));
        vis[1][1] = 1;
        while (!q.empty()) {
            auto [x, y] = q.front(); q.pop();
            for (int d = 0; d < 6; ++d) {
                int nx = x + DX[d], ny = y + DY[d];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if (((nx + ny) & 1) != 0) continue; // ensure even parity
                if (a[nx][ny] != -1) continue;
                int x1 = min(x, nx), y1 = min(y, ny);
                int x2 = max(x, nx), y2 = max(y, ny);
                if (x1 + y1 + 2 > x2 + y2) continue; // ensure non-adjacent
                int ans = ask(x1, y1, x2, y2);
                a[nx][ny] = (ans ? a[x][y] : (1 - a[x][y]));
                if (!vis[nx][ny]) {
                    vis[nx][ny] = 1;
                    q.push({nx, ny});
                }
            }
        }
    }

    // Fill odd parity cells (starting from (1,2))
    if (n >= 2) {
        a[1][2] = 0; // arbitrary, will be flipped later if needed
        queue<pair<int,int>> q;
        q.push({1,2});
        vector<vector<char>> vis(n + 1, vector<char>(n + 1, 0));
        vis[1][2] = 1;
        while (!q.empty()) {
            auto [x, y] = q.front(); q.pop();
            for (int d = 0; d < 6; ++d) {
                int nx = x + DX[d], ny = y + DY[d];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if (((nx + ny) & 1) != 1) continue; // ensure odd parity
                if (a[nx][ny] != -1) continue;
                int x1 = min(x, nx), y1 = min(y, ny);
                int x2 = max(x, nx), y2 = max(y, ny);
                if (x1 + y1 + 2 > x2 + y2) continue;
                int ans = ask(x1, y1, x2, y2);
                a[nx][ny] = (ans ? a[x][y] : (1 - a[x][y]));
                if (!vis[nx][ny]) {
                    vis[nx][ny] = 1;
                    q.push({nx, ny});
                }
            }
        }
    }

    // Determine the correct orientation (flip of odd cells)
    int flipOdd = 0;
    bool decided = false;

    // Try pairs at distance 3 first
    for (int i = 1; i <= n && !decided; ++i) {
        for (int j = 1; j <= n && !decided; ++j) {
            // shape (2,1)
            if (i + 2 <= n && j + 1 <= n) {
                bool b0 = checkRect(i, j, i + 2, j + 1, 0);
                bool b1 = checkRect(i, j, i + 2, j + 1, 1);
                if (b0 != b1) {
                    int ans = ask(i, j, i + 2, j + 1);
                    flipOdd = (ans != b0);
                    decided = true;
                    break;
                }
            }
            // shape (1,2)
            if (i + 1 <= n && j + 2 <= n) {
                bool b0 = checkRect(i, j, i + 1, j + 2, 0);
                bool b1 = checkRect(i, j, i + 1, j + 2, 1);
                if (b0 != b1) {
                    int ans = ask(i, j, i + 1, j + 2);
                    flipOdd = (ans != b0);
                    decided = true;
                    break;
                }
            }
        }
    }

    // If not decided, scan more general pairs (should rarely be needed)
    if (!decided) {
        for (int x1 = 1; x1 <= n && !decided; ++x1) {
            for (int y1 = 1; y1 <= n && !decided; ++y1) {
                for (int x2 = x1; x2 <= n && !decided; ++x2) {
                    for (int y2 = y1; y2 <= n && !decided; ++y2) {
                        if (x1 + y1 + 2 > x2 + y2) continue;
                        bool b0 = checkRect(x1, y1, x2, y2, 0);
                        bool b1 = checkRect(x1, y1, x2, y2, 1);
                        if (b0 != b1) {
                            int ans = ask(x1, y1, x2, y2);
                            flipOdd = (ans != b0);
                            decided = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    // Apply flip to odd cells
    if (flipOdd) {
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= n; ++j)
                if (((i + j) & 1) == 1)
                    a[i][j] ^= 1;
    }

    // Output the final grid
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j)
            cout << a[i][j];
        cout << endl;
    }
    cout.flush();

    return 0;
}