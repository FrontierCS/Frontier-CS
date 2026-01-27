#include <bits/stdc++.h>
using namespace std;

struct Cell { int x, y; };

bool isSubsequence(const vector<int>& p, const vector<int>& q) {
    int j = 0;
    for (int x : p) {
        if (j < (int)q.size() && x == q[j]) j++;
    }
    return j == (int)q.size();
}

bool generatePath(int n, int m, int L, int R, int Sx, int Sy,
                  const vector<int>& rowOrder,
                  vector<Cell>& pathOut) {
    vector<vector<bool>> vis(n+1, vector<bool>(m+1,false));
    auto add = [&](int x, int y)->bool{
        if (x < 1 || x > n || y < 1 || y > m) return false;
        if (vis[x][y]) return false;
        vis[x][y] = true;
        pathOut.push_back({x,y});
        return true;
    };

    // Start
    if (!add(Sx, L)) return false;
    int curX = Sx, curY = L;

    // First row sweep from L to R
    for (int y = L+1; y <= R; ++y) {
        if (!add(curX, y)) return false;
    }
    curY = R;

    // Process remaining rows in order
    for (int i = 1; i < (int)rowOrder.size(); ++i) {
        int prevRow = rowOrder[i-1];
        int nextRow = rowOrder[i];

        // Move vertically to nextRow at current end curY (must be L or R)
        if (abs(nextRow - prevRow) == 1) {
            int nx = (nextRow > prevRow) ? prevRow + 1 : prevRow - 1;
            if (!add(nx, curY)) return false;
            curX = nextRow;
        } else {
            // Need to bridge via outside-of-strip
            if (curY == R) {
                if (R == m) return false;
                if (!add(curX, R+1)) return false; // step outside
                int yOutside = R+1;
                int sgn = (nextRow > curX) ? 1 : -1;
                for (int x = curX + sgn; x != nextRow + sgn; x += sgn) {
                    if (!add(x, yOutside)) return false;
                }
                if (!add(nextRow, R)) return false; // re-enter at R
                curX = nextRow;
            } else if (curY == L) {
                if (L == 1) return false;
                if (!add(curX, L-1)) return false; // step outside
                int yOutside = L-1;
                int sgn = (nextRow > curX) ? 1 : -1;
                for (int x = curX + sgn; x != nextRow + sgn; x += sgn) {
                    if (!add(x, yOutside)) return false;
                }
                if (!add(nextRow, L)) return false; // re-enter at L
                curX = nextRow;
            } else {
                return false; // should not happen
            }
        }

        // Sweep the new row
        int targetY = (curY == L ? R : L);
        if (targetY > curY) {
            for (int y = curY + 1; y <= targetY; ++y) {
                if (!add(curX, y)) return false;
            }
        } else {
            for (int y = curY - 1; y >= targetY; --y) {
                if (!add(curX, y)) return false;
            }
        }
        curY = targetY;
    }

    // Verify all required cells visited
    for (int x = 1; x <= n; ++x) {
        for (int y = L; y <= R; ++y) {
            if (!vis[x][y]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Basic validation for q: must be within [1, n]
    for (int x : q) {
        if (x < 1 || x > n) {
            cout << "NO\n";
            return 0;
        }
    }
    // Sy is guaranteed to be L according to statement, but we do not rely on it beyond start.

    vector<pair<int,int>> plans; // (d0, reenterTop) as (dir, topFlag)
    // dir: +1 downwards, -1 upwards. topFlag 0/1.
    plans.push_back({+1, 0});
    plans.push_back({+1, 1});
    plans.push_back({-1, 0});
    plans.push_back({-1, 1});

    vector<Cell> bestPath;
    bool found = false;

    for (auto [d0, topFlag] : plans) {
        // Build row order
        vector<int> rowOrder;

        // Block A
        int r = Sx;
        int boundary = (d0 == +1 ? n : 1);
        while (true) {
            rowOrder.push_back(r);
            if (r == boundary) break;
            r += d0;
        }

        // Block B (remaining side)
        if (d0 == +1) {
            // remaining rows are 1..Sx-1
            if (Sx - 1 >= 1) {
                if (topFlag == 0) {
                    for (int rr = Sx - 1; rr >= 1; --rr) rowOrder.push_back(rr);
                } else {
                    for (int rr = 1; rr <= Sx - 1; ++rr) rowOrder.push_back(rr);
                }
            }
        } else {
            // d0 == -1, remaining rows are Sx+1..n
            if (Sx + 1 <= n) {
                if (topFlag == 0) {
                    for (int rr = Sx + 1; rr <= n; ++rr) rowOrder.push_back(rr);
                } else {
                    for (int rr = n; rr >= Sx + 1; --rr) rowOrder.push_back(rr);
                }
            }
        }

        // Check subsequence condition
        if (!isSubsequence(rowOrder, q)) continue;

        // Generate path for this order
        vector<Cell> path;
        if (!generatePath(n, m, L, R, Sx, Sy, rowOrder, path)) continue;

        if (!found || path.size() < bestPath.size()) {
            bestPath = std::move(path);
            found = true;
        }
    }

    if (!found) {
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n";
    cout << bestPath.size() << "\n";
    for (auto &c : bestPath) {
        cout << c.x << " " << c.y << "\n";
    }

    return 0;
}