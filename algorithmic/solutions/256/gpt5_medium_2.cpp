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

bool inb(int x, int y) {
    return x >= 1 && x <= n && y >= 1 && y <= n;
}

void fill_parity(int sx, int sy) {
    queue<pair<int,int>> q;
    q.push({sx, sy});
    // Moves at manhattan distance 2
    int dx[6] = {2, 0, 1, -2, 0, -1};
    int dy[6] = {0, 2, 1, 0, -2, -1};
    while(!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int k = 0; k < 6; ++k) {
            int nx = x + dx[k], ny = y + dy[k];
            if (!inb(nx, ny)) continue;
            if (a[nx][ny] != -1) continue;
            int x1 = min(x, nx), y1 = min(y, ny);
            int x2 = max(x, nx), y2 = max(y, ny);
            // ensure valid query: distance is exactly 2, monotonic
            if (x1 + y1 + 2 > x2 + y2) continue;
            int r = ask(x1, y1, x2, y2);
            // r == 1 if exists palindromic path; for distance 2 this means endpoints equal
            if (r == 1) a[nx][ny] = a[x][y];
            else a[nx][ny] = a[x][y] ^ 1;
            q.push({nx, ny});
        }
    }
}

int getVal(int i, int j, int flip) {
    int v = a[i][j];
    if ((i + j) % 2 == 1) v ^= flip;
    return v;
}

bool existPalinPathsSmallD(int x1, int y1, int x2, int y2, int flip) {
    int dx = x2 - x1, dy = y2 - y1;
    int D = dx + dy;
    if (D < 0) return false;
    if (x1 + y1 + 2 > x2 + y2) return false;
    // Early check: endpoints must be equal
    if (getVal(x1,y1,flip) != getVal(x2,y2,flip)) return false;

    // Enumerate all monotonic paths from (x1,y1) to (x2,y2)
    // D expected small (we will search for D up to 5)
    vector<pair<int,int>> path;
    path.reserve(D+1);
    function<bool(int,int,int,int)> dfs = [&](int x, int y, int rd, int dd)->bool{
        path.emplace_back(x,y);
        if (rd==0 && dd==0) {
            // Check palindrome
            int m = (int)path.size();
            bool ok = true;
            for (int i = 0, j = m-1; i < j; ++i, --j) {
                if (getVal(path[i].first, path[i].second, flip) != getVal(path[j].first, path[j].second, flip)) {
                    ok = false; break;
                }
            }
            path.pop_back();
            return ok;
        }
        bool res = false;
        if (rd > 0) {
            res = res || dfs(x, y+1, rd-1, dd);
            if (res) { path.pop_back(); return true; }
        }
        if (dd > 0) {
            res = res || dfs(x+1, y, rd, dd-1);
            if (res) { path.pop_back(); return true; }
        }
        path.pop_back();
        return res;
    };
    return dfs(x1, y1, dy, dx);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    a.assign(n+1, vector<int>(n+1, -1));

    // Known cells
    a[1][1] = 1;
    // Fill all even parity cells
    fill_parity(1, 1);

    // Fill odd parity cells with an arbitrary start value
    if (n >= 2) {
        a[1][2] = 0;
        fill_parity(1, 2);
    }

    // Find a discriminating query to determine flip for odd cells
    int fx1=0, fy1=0, fx2=0, fy2=0;
    bool found = false;
    // Try D = 3 first
    for (int D = 3; D <= 5 && !found; ++D) {
        for (int x1 = 1; x1 <= n; ++x1) {
            for (int y1 = 1; y1 <= n; ++y1) {
                int maxdx = min(n - x1, D);
                for (int dx = 0; dx <= maxdx; ++dx) {
                    int dy = D - dx;
                    int x2 = x1 + dx;
                    int y2 = y1 + dy;
                    if (y2 > n) continue;
                    if (x1 + y1 + 2 > x2 + y2) continue;
                    // Ensure cells are within bounds (already ensured)
                    bool p0 = existPalinPathsSmallD(x1,y1,x2,y2,0);
                    bool p1 = existPalinPathsSmallD(x1,y1,x2,y2,1);
                    if (p0 != p1) {
                        fx1 = x1; fy1 = y1; fx2 = x2; fy2 = y2;
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            if (found) break;
        }
    }

    int flip = 0;
    if (found) {
        int realAns = ask(fx1, fy1, fx2, fy2);
        bool p0 = existPalinPathsSmallD(fx1,fy1,fx2,fy2,0);
        flip = (realAns == (int)p0) ? 0 : 1;
    } else {
        // Fallback: if not found (shouldn't happen), no additional query; assume flip = 0
        flip = 0;
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int v = getVal(i,j,flip);
            cout << v;
        }
        cout << endl;
    }
    cout.flush();
    return 0;
}