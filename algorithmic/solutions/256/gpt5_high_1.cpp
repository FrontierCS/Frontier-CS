#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> val;

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

void bfs_fill(int sx, int sy) {
    queue<pair<int,int>> q;
    q.push({sx, sy});
    int start_par = (sx + sy) & 1;
    int dx[6] = {2, 0, 1, -2, 0, -1};
    int dy[6] = {0, 2, 1, 0, -2, -1};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int dir = 0; dir < 6; ++dir) {
            int nx = x + dx[dir];
            int ny = y + dy[dir];
            if (nx < 1 || ny < 1 || nx > n || ny > n) continue;
            if (((nx + ny) & 1) != start_par) continue;
            if (val[nx][ny] != -1) continue;
            int ax = x, ay = y, bx = nx, by = ny;
            if (ax > bx || ay > by) { // ensure ax<=bx and ay<=by
                swap(ax, bx);
                swap(ay, by);
            }
            int r = ask(ax, ay, bx, by);
            val[nx][ny] = val[x][y] ^ (1 - r);
            q.push({nx, ny});
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;
    val.assign(n + 1, vector<int>(n + 1, -1));
    // Fill even parity starting from (1,1)=1
    val[1][1] = 1;
    bfs_fill(1, 1);
    // Fill odd parity starting from (1,2)=0 (arbitrary)
    val[1][2] = 0;
    bfs_fill(1, 2);

    // Find a segment of length 3 in a row or column where (a==d) xor (b==c) == 0
    int x1 = -1, y1 = -1, x2 = -1, y2 = -1;
    bool predPal = false;
    bool found = false;

    // Rows
    for (int i = 1; i <= n && !found; ++i) {
        for (int j = 1; j + 3 <= n; ++j) {
            int a = val[i][j];
            int b = val[i][j+1];
            int c = val[i][j+2];
            int d = val[i][j+3];
            int condXor = (a == d) ^ (b == c);
            if (condXor == 0) {
                x1 = i; y1 = j; x2 = i; y2 = j+3;
                predPal = (a == d) && (b == c);
                found = true;
                break;
            }
        }
    }
    // Columns
    if (!found) {
        for (int j = 1; j <= n && !found; ++j) {
            for (int i = 1; i + 3 <= n; ++i) {
                int a = val[i][j];
                int b = val[i+1][j];
                int c = val[i+2][j];
                int d = val[i+3][j];
                int condXor = (a == d) ^ (b == c);
                if (condXor == 0) {
                    x1 = i; y1 = j; x2 = i+3; y2 = j;
                    predPal = (a == d) && (b == c);
                    found = true;
                    break;
                }
            }
        }
    }

    if (found) {
        int resp = ask(x1, y1, x2, y2);
        if (resp != (int)predPal) {
            for (int i = 1; i <= n; ++i)
                for (int j = 1; j <= n; ++j)
                    if (((i + j) & 1) == 1)
                        val[i][j] ^= 1;
        }
    } else {
        // As a fallback (should not occur), just ensure consistency by one more query using a simple pattern
        // We'll use (1,1) to (1,3) if possible, otherwise (1,1) to (3,1)
        if (n >= 4) {
            int a = val[1][1], b = val[1][2], c = val[1][3], d = val[1][4];
            int condXor = (a == d) ^ (b == c);
            bool pred = (condXor == 0) ? ((a == d) && (b == c)) : false; // if condXor==1, palindrome impossible
            int resp = ask(1, 1, 1, 4);
            if (condXor == 0 && resp != (int)pred) {
                for (int i = 1; i <= n; ++i)
                    for (int j = 1; j <= n; ++j)
                        if (((i + j) & 1) == 1)
                            val[i][j] ^= 1;
            }
        } else {
            // n == 3 case shouldn't reach here because a segment exists
        }
    }

    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) cout << val[i][j];
        cout << '\n';
    }
    cout.flush();
    return 0;
}