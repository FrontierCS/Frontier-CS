#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> a;

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

bool inb(int x, int y) {
    return x >= 1 && x <= n && y >= 1 && y <= n;
}

void fill_from_seed(int sx, int sy) {
    static const int dx[] = {2, 0, -2, 0, 1, -1};
    static const int dy[] = {0, 2, 0, -2, 1, -1};
    queue<pair<int,int>> q;
    q.push({sx, sy});
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int dir = 0; dir < 6; ++dir) {
            int nx = x + dx[dir], ny = y + dy[dir];
            if (!inb(nx, ny)) continue;
            if (a[nx][ny] != -1) continue;
            int x1 = min(x, nx), y1 = min(y, ny), x2 = max(x, nx), y2 = max(y, ny);
            // distance is exactly 2
            int res = ask(x1, y1, x2, y2);
            if (res == 1) a[nx][ny] = a[x][y];
            else a[nx][ny] = a[x][y] ^ 1;
            q.push({nx, ny});
        }
    }
}

int val(int i, int j, int flipOdd) {
    int v = a[i][j];
    if (((i + j) & 1) && flipOdd) v ^= 1;
    return v;
}

bool check_path_pal_small(int x1, int y1, int x2, int y2, int flipOdd) {
    int dx = x2 - x1, dy = y2 - y1;
    if (dx < 0 || dy < 0) return false;
    int L = dx + dy; // number of moves
    // Generate all paths with dx Ds (down) and dy Rs (right)
    // For small L (<= 4 or 5), brute force all permutations
    // We'll use recursion/backtracking
    vector<char> path(L);
    function<bool(int,int,int,int,int,int)> dfs = [&](int pos, int cx, int cy, int rd, int rr, int last) -> bool {
        if (pos == L) {
            // Evaluate sequence along the path
            int px = x1, py = y1;
            vector<int> seq;
            seq.push_back(val(px, py, flipOdd));
            for (int k = 0; k < L; ++k) {
                if (path[k] == 'D') ++px;
                else ++py;
                seq.push_back(val(px, py, flipOdd));
            }
            // Check palindrome
            int sz = (int)seq.size();
            for (int i = 0; i < sz/2; ++i) {
                if (seq[i] != seq[sz-1-i]) return false;
            }
            return true;
        }
        if (rd > 0) {
            path[pos] = 'D';
            if (dfs(pos+1, cx+1, cy, rd-1, rr, 0)) return true;
        }
        if (rr > 0) {
            path[pos] = 'R';
            if (dfs(pos+1, cx, cy+1, rd, rr-1, 1)) return true;
        }
        return false;
    };
    return dfs(0, 0, 0, dx, dy, -1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;
    a.assign(n+1, vector<int>(n+1, -1));
    a[1][1] = 1;
    fill_from_seed(1, 1); // fill all even parity cells
    if (a[n][n] != -1) a[n][n] = a[n][n]; // given bottom-right is 0, but we proceed based on queries
    a[1][2] = 0; // arbitrary seed for odd parity
    fill_from_seed(1, 2); // fill all odd parity cells relative to this seed

    // Find a pair (x1,y1)-(x2,y2) with distance 3 or 4 where prediction differs under flipping odd parity
    bool resolved = false;
    int rx1=0, ry1=0, rx2=0, ry2=0;
    // Try distance 3 first
    for (int d = 3; d <= 4 && !resolved; ++d) {
        for (int x1 = 1; x1 <= n && !resolved; ++x1) {
            for (int y1 = 1; y1 <= n && !resolved; ++y1) {
                int dxs[] = {d, 0};
                for (int t = 0; t < 2 && !resolved; ++t) {
                    int dx = dxs[t], dy = d - dx;
                    int x2 = x1 + dx, y2 = y1 + dy;
                    if (!inb(x2, y2)) continue;
                    bool r0 = check_path_pal_small(x1, y1, x2, y2, 0);
                    bool r1 = check_path_pal_small(x1, y1, x2, y2, 1);
                    if (r0 != r1) {
                        rx1 = x1; ry1 = y1; rx2 = x2; ry2 = y2;
                        resolved = true;
                    }
                }
            }
        }
    }

    if (resolved) {
        int realAns = ask(rx1, ry1, rx2, ry2);
        bool pred0 = check_path_pal_small(rx1, ry1, rx2, ry2, 0);
        if (realAns != pred0) {
            for (int i = 1; i <= n; ++i) {
                for (int j = 1; j <= n; ++j) {
                    if ((i + j) & 1) a[i][j] ^= 1;
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