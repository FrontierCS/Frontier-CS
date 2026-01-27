#include <bits/stdc++.h>
using namespace std;

const int MAXN = 50;

int n;
int a[51][51];
int a_flip[51][51];
unsigned char good0[51][51][51][51];
unsigned char good1[51][51][51][51];

int query(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    // Initialize grid with -1 (unknown)
    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            a[i][j] = -1;

    queue<pair<int,int>> q;
    a[1][1] = 1;
    q.push({1, 1});
    if (n >= 2) {
        a[1][2] = 0; // arbitrary base for odd parity
        q.push({1, 2});
    }

    // BFS using distance-2 moves with monotone-compatible pairs
    const int dx[6] = {2, 0, 1, -2, 0, -1};
    const int dy[6] = {0, 2, 1, 0, -2, -1};

    while (!q.empty()) {
        auto cur = q.front(); q.pop();
        int x = cur.first;
        int y = cur.second;

        for (int k = 0; k < 6; ++k) {
            int nx = x + dx[k];
            int ny = y + dy[k];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (a[nx][ny] != -1) continue;

            int x1 = x, y1 = y, x2 = nx, y2 = ny;
            if (x1 > x2) {
                swap(x1, x2);
                swap(y1, y2);
            }
            // Now (x1,y1) is top-left, (x2,y2) bottom-right, distance is 2
            int ans = query(x1, y1, x2, y2);
            bool same = (ans == 1);
            a[nx][ny] = a[x][y] ^ (same ? 0 : 1);
            q.push({nx, ny});
        }
    }

    // Build flipped grid for odd parity cells
    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            if ((i + j) & 1)
                a_flip[i][j] = a[i][j] ^ 1;
            else
                a_flip[i][j] = a[i][j];

    // Precompute palindromic-path existence for all rectangles for both boards
    int maxLen = 2 * (n - 1);
    for (int len = 0; len <= maxLen; ++len) {
        for (int x1 = 1; x1 <= n; ++x1) {
            for (int y1 = 1; y1 <= n; ++y1) {
                int max_dx = min(len, n - x1);
                for (int dxv = 0; dxv <= max_dx; ++dxv) {
                    int x2 = x1 + dxv;
                    int dyv = len - dxv;
                    int y2 = y1 + dyv;
                    if (y2 > n) continue;

                    // Board a -> good0
                    if (a[x1][y1] != a[x2][y2]) {
                        good0[x1][y1][x2][y2] = 0;
                    } else if (len <= 1) {
                        good0[x1][y1][x2][y2] = 1;
                    } else {
                        unsigned char ok = 0;
                        if (x1 + 1 <= x2 - 1 && good0[x1 + 1][y1][x2 - 1][y2]) ok = 1;
                        if (!ok && x1 + 1 <= x2 && y1 <= y2 - 1 &&
                            good0[x1 + 1][y1][x2][y2 - 1]) ok = 1;
                        if (!ok && y1 + 1 <= y2 && x1 <= x2 - 1 &&
                            good0[x1][y1 + 1][x2 - 1][y2]) ok = 1;
                        if (!ok && y1 + 1 <= y2 - 1 &&
                            good0[x1][y1 + 1][x2][y2 - 1]) ok = 1;
                        good0[x1][y1][x2][y2] = ok;
                    }

                    // Board a_flip -> good1
                    if (a_flip[x1][y1] != a_flip[x2][y2]) {
                        good1[x1][y1][x2][y2] = 0;
                    } else if (len <= 1) {
                        good1[x1][y1][x2][y2] = 1;
                    } else {
                        unsigned char ok = 0;
                        if (x1 + 1 <= x2 - 1 && good1[x1 + 1][y1][x2 - 1][y2]) ok = 1;
                        if (!ok && x1 + 1 <= x2 && y1 <= y2 - 1 &&
                            good1[x1 + 1][y1][x2][y2 - 1]) ok = 1;
                        if (!ok && y1 + 1 <= y2 && x1 <= x2 - 1 &&
                            good1[x1][y1 + 1][x2 - 1][y2]) ok = 1;
                        if (!ok && y1 + 1 <= y2 - 1 &&
                            good1[x1][y1 + 1][x2][y2 - 1]) ok = 1;
                        good1[x1][y1][x2][y2] = ok;
                    }
                }
            }
        }
    }

    // Find a rectangle where answers differ between the two boards
    bool found = false;
    int sx = 1, sy = 1, tx = n, ty = n;
    for (int len = 2; len <= maxLen && !found; ++len) {
        for (int x1 = 1; x1 <= n && !found; ++x1) {
            for (int y1 = 1; y1 <= n && !found; ++y1) {
                int max_dx = min(len, n - x1);
                for (int dxv = 0; dxv <= max_dx; ++dxv) {
                    int x2 = x1 + dxv;
                    int dyv = len - dxv;
                    int y2 = y1 + dyv;
                    if (y2 > n) continue;
                    if (good0[x1][y1][x2][y2] != good1[x1][y1][x2][y2]) {
                        sx = x1; sy = y1; tx = x2; ty = y2;
                        found = true;
                        break;
                    }
                }
            }
        }
    }

    bool useFlip = false;
    if (found) {
        int res = query(sx, sy, tx, ty);
        if (res == (int)good1[sx][sy][tx][ty]) useFlip = true;
    }

    cout << "!\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int v = useFlip ? a_flip[i][j] : a[i][j];
            cout << v;
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}