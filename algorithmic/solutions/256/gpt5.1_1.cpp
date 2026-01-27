#include <bits/stdc++.h>
using namespace std;

const int MAXN = 50;

int n;
int a[MAXN + 1][MAXN + 1]; // grid with even cells true, odd cells predicted

// DP arrays: f1 for grid with current odd, f2 for grid with flipped odd
static bool f1[51][51][51][51];
static bool f2[51][51][51][51];

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

inline int get1(int x, int y) {
    return a[x][y];
}

inline int get2(int x, int y) {
    return ((x + y) & 1) ? (a[x][y] ^ 1) : a[x][y];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            a[i][j] = -1;

    // Even parity BFS from (1,1) with known value 1
    a[1][1] = 1;
    queue<pair<int,int>> q;
    q.push({1, 1});
    const int dx[6] = {2, 0, -2, 0, 1, -1};
    const int dy[6] = {0, 2, 0, -2, 1, -1};

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (int dir = 0; dir < 6; ++dir) {
            int nx = x + dx[dir];
            int ny = y + dy[dir];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (((nx + ny) & 1) != 0) continue; // only even parity here
            if (a[nx][ny] != -1) continue;
            int x1 = min(x, nx), y1 = min(y, ny);
            int x2 = max(x, nx), y2 = max(y, ny);
            int res = ask(x1, y1, x2, y2);
            if (res == 1) a[nx][ny] = a[x][y];
            else a[nx][ny] = a[x][y] ^ 1;
            q.push({nx, ny});
        }
    }

    // Odd parity BFS from (1,2) with arbitrary starting value 0
    int ox = 1, oy = 2;
    if (oy <= n) {
        a[ox][oy] = 0;
        q.push({ox, oy});
        while (!q.empty()) {
            auto [x, y] = q.front();
            q.pop();
            for (int dir = 0; dir < 6; ++dir) {
                int nx = x + dx[dir];
                int ny = y + dy[dir];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if (((nx + ny) & 1) != 1) continue; // only odd parity here
                if (a[nx][ny] != -1) continue;
                int x1 = min(x, nx), y1 = min(y, ny);
                int x2 = max(x, nx), y2 = max(y, ny);
                int res = ask(x1, y1, x2, y2);
                if (res == 1) a[nx][ny] = a[x][y];
                else a[nx][ny] = a[x][y] ^ 1;
                q.push({nx, ny});
            }
        }
    }

    // DP for both candidate grids
    int maxD = 2 * (n - 1);
    for (int D = 0; D <= maxD; ++D) {
        for (int x1 = 1; x1 <= n; ++x1) {
            for (int y1 = 1; y1 <= n; ++y1) {
                int x2_min = x1;
                int x2_max = min(n, x1 + D);
                for (int x2 = x2_min; x2 <= x2_max; ++x2) {
                    int y2 = y1 + D - (x2 - x1);
                    if (y2 < y1 || y2 > n) continue;

                    if (D == 0) {
                        f1[x1][y1][x2][y2] = true;
                        f2[x1][y1][x2][y2] = true;
                    } else if (D == 1) {
                        f1[x1][y1][x2][y2] = (get1(x1, y1) == get1(x2, y2));
                        f2[x1][y1][x2][y2] = (get2(x1, y1) == get2(x2, y2));
                    } else {
                        int v1s = get1(x1, y1), v1t = get1(x2, y2);
                        int v2s = get2(x1, y1), v2t = get2(x2, y2);
                        bool ok1 = false, ok2 = false;

                        if (v1s == v1t) {
                            if (x1 + 1 <= x2) {
                                if (x1 + 1 <= x2 - 1)
                                    ok1 |= f1[x1 + 1][y1][x2 - 1][y2];
                                if (y2 - 1 >= y1)
                                    ok1 |= f1[x1 + 1][y1][x2][y2 - 1];
                            }
                            if (y1 + 1 <= y2) {
                                if (x2 - 1 >= x1)
                                    ok1 |= f1[x1][y1 + 1][x2 - 1][y2];
                                if (y2 - 1 >= y1 + 1)
                                    ok1 |= f1[x1][y1 + 1][x2][y2 - 1];
                            }
                        }

                        if (v2s == v2t) {
                            if (x1 + 1 <= x2) {
                                if (x1 + 1 <= x2 - 1)
                                    ok2 |= f2[x1 + 1][y1][x2 - 1][y2];
                                if (y2 - 1 >= y1)
                                    ok2 |= f2[x1 + 1][y1][x2][y2 - 1];
                            }
                            if (y1 + 1 <= y2) {
                                if (x2 - 1 >= x1)
                                    ok2 |= f2[x1][y1 + 1][x2 - 1][y2];
                                if (y2 - 1 >= y1 + 1)
                                    ok2 |= f2[x1][y1 + 1][x2][y2 - 1];
                            }
                        }

                        f1[x1][y1][x2][y2] = ok1;
                        f2[x1][y1][x2][y2] = ok2;
                    }
                }
            }
        }
    }

    // Find a pair where answers differ between two candidate grids
    int sx1 = -1, sy1 = -1, sx2 = -1, sy2 = -1;
    bool found = false;
    for (int D = 2; D <= maxD && !found; ++D) {
        for (int x1 = 1; x1 <= n && !found; ++x1) {
            for (int y1 = 1; y1 <= n && !found; ++y1) {
                int x2_min = x1;
                int x2_max = min(n, x1 + D);
                for (int x2 = x2_min; x2 <= x2_max; ++x2) {
                    int y2 = y1 + D - (x2 - x1);
                    if (y2 < y1 || y2 > n) continue;
                    if (f1[x1][y1][x2][y2] != f2[x1][y1][x2][y2]) {
                        sx1 = x1; sy1 = y1; sx2 = x2; sy2 = y2;
                        found = true;
                        break;
                    }
                }
            }
        }
    }

    int flip = 0;
    if (found) {
        int realAns = ask(sx1, sy1, sx2, sy2);
        bool b1 = f1[sx1][sy1][sx2][sy2];
        flip = (realAns == (b1 ? 1 : 0)) ? 0 : 1;
    } else {
        flip = 0; // theoretically impossible, but keep current grid
    }

    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int v = a[i][j];
            if ((i + j) & 1) v ^= flip;
            cout << v;
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}