#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> a;

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

void fill_parity(int parity, vector<pair<int,int>> seeds) {
    queue<pair<int,int>> q;
    vector<vector<char>> vis(n+1, vector<char>(n+1, 0));
    for (auto &p : seeds) {
        q.push(p);
        vis[p.first][p.second] = 1;
    }
    int dx[6] = {2, 1, 0, -2, -1, 0};
    int dy[6] = {0, 1, 2, 0, -1, -2};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int k = 0; k < 6; ++k) {
            int nx = x + dx[k], ny = y + dy[k];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (((nx + ny) & 1) != parity) continue;
            if (a[nx][ny] != -1) continue;
            int r;
            if (nx <= x && ny <= y) r = ask(nx, ny, x, y);
            else r = ask(x, y, nx, ny);
            a[nx][ny] = (r ? a[x][y] : 1 - a[x][y]);
            if (!vis[nx][ny]) {
                vis[nx][ny] = 1;
                q.push({nx, ny});
            }
        }
    }
}

bool find_pair(int &x1, int &y1, int &x2, int &y2) {
    // Shape dx=1, dy=2
    for (int i = 1; i + 1 <= n; ++i) {
        for (int j = 1; j + 2 <= n; ++j) {
            bool e1 = (a[i][j+1] == a[i][j+2]);
            bool e2 = (a[i][j+1] == a[i+1][j+1]);
            bool e3 = (a[i+1][j] == a[i+1][j+1]);
            if (!(e1 == e2 && e2 == e3)) {
                x1 = i; y1 = j; x2 = i+1; y2 = j+2;
                return true;
            }
        }
    }
    // Shape dx=2, dy=1
    for (int i = 1; i + 2 <= n; ++i) {
        for (int j = 1; j + 1 <= n; ++j) {
            bool e1 = (a[i+1][j] == a[i+2][j]);
            bool e2 = (a[i+1][j] == a[i+1][j+1]);
            bool e3 = (a[i][j+1] == a[i+1][j+1]);
            if (!(e1 == e2 && e2 == e3)) {
                x1 = i; y1 = j; x2 = i+2; y2 = j+1;
                return true;
            }
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;
    a.assign(n+1, vector<int>(n+1, -1));

    // Known cells
    a[1][1] = 1;
    a[n][n] = 0;

    // Fill even parity (0)
    fill_parity(0, {{1,1}});

    // Guess odd parity anchor and fill
    if (n >= 2) {
        a[1][2] = 0; // arbitrary guess
        fill_parity(1, {{1,2}});
    }

    // Disambiguate using a pair at distance 3
    int x1 = -1, y1 = -1, x2 = -1, y2 = -1;
    bool ok = find_pair(x1, y1, x2, y2);
    if (!ok) {
        // Fallback: in practice this should not happen
        // Just output as is
    } else {
        int res = ask(x1, y1, x2, y2);
        int predicted = (a[x1][y1] == a[x2][y2]) ? 1 : 0;
        if (res != predicted) {
            // Flip all odd parity cells
            for (int i = 1; i <= n; ++i) {
                for (int j = 1; j <= n; ++j) {
                    if ((i + j) % 2 == 1) a[i][j] ^= 1;
                }
            }
        }
    }

    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) cout << a[i][j];
        cout << '\n';
    }
    cout.flush();
    return 0;
}