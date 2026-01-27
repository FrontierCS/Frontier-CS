#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, -1));
    grid[1][1] = 1;
    vector<vector<bool>> vis(n + 1, vector<bool>(n + 1, false));
    vis[1][1] = true;
    queue<pair<int, int>> q;
    q.push({1, 1});
    vector<pair<int, int>> jumps = {{0, 2}, {1, 1}, {2, 0}};
    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (auto [dx, dy] : jumps) {
            int nx = x + dx, ny = y + dy;
            if (nx <= n && ny <= n && (nx + ny) % 2 == 0 && !vis[nx][ny]) {
                cout << "? " << x << " " << y << " " << nx << " " << ny << endl;
                cout.flush();
                int res;
                cin >> res;
                if (res == -1) exit(0);
                int valn = (res == 1 ? grid[x][y] : 1 - grid[x][y]);
                grid[nx][ny] = valn;
                vis[nx][ny] = true;
                q.push({nx, ny});
            }
        }
    }
    // now odds
    vector<pair<int, int>> odd_list;
    map<pair<int, int>, int> oindex;
    int mm = 0;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            if ((i + j) % 2 == 1) {
                odd_list.emplace_back(i, j);
                oindex[{i, j}] = mm++;
            }
        }
    }
    vector<int> parent(mm), xortopar(mm, 0), rankk(mm, 0);
    for (int i = 0; i < mm; i++) parent[i] = i;
    auto findf = [&](auto&& self, int x) -> int {
        if (parent[x] != x) {
            int p = self(self, parent[x]);
            xortopar[x] ^= xortopar[parent[x]];
            parent[x] = p;
        }
        return parent[x];
    };
    auto unionf = [&](int a, int b, int d) {
        int pa = findf(findf, a), pb = findf(findf, b);
        if (pa == pb) {
            if ((xortopar[a] ^ xortopar[b]) != d) {
                // contradiction, ignore
            }
            return;
        }
        int delta = xortopar[a] ^ xortopar[b] ^ d;
        if (rankk[pa] < rankk[pb]) {
            parent[pa] = pb;
            xortopar[pa] = delta;
        } else if (rankk[pa] > rankk[pb]) {
            parent[pb] = pa;
            xortopar[pb] = delta;
        } else {
            parent[pa] = pb;
            xortopar[pa] = delta;
            rankk[pb]++;
        }
    };
    for (int ii = 0; ii < mm; ii++) {
        auto [x, y] = odd_list[ii];
        for (auto [dx, dy] : jumps) {
            int nx = x + dx, ny = y + dy;
            if (nx <= n && ny <= n && (nx + ny) % 2 == 1) {
                int iu = ii, iv = oindex[{nx, ny}];
                cout << "? " << x << " " << y << " " << nx << " " << ny << endl;
                cout.flush();
                int res;
                cin >> res;
                if (res == -1) exit(0);
                int dd = (res == 1 ? 0 : 1);
                unionf(iu, iv, dd);
            }
        }
    }
    // now assign temp 0
    int some = 0;
    int ther = findf(findf, some);
    vector<int> valo(mm);
    for (int k = 0; k < mm; k++) {
        int r = findf(findf, k);
        valo[k] = xortopar[k] ^ 0;
        auto [ii, jj] = odd_list[k];
        grid[ii][jj] = valo[k];
    }
    // grid now grid1
    vector<vector<int>> grid2(n + 1, vector<int>(n + 1));
    for (int i = 0; i <= n; i++) {
        for (int j = 0; j <= n; j++) {
            grid2[i][j] = grid[i][j];
        }
    }
    for (int k = 0; k < mm; k++) {
        auto [ii, jj] = odd_list[k];
        grid2[ii][jj] = 1 - grid2[ii][jj];
    }
    // now tests
    vector<tuple<int, int, int, int>> tests = {
        {1, 1, 2, 3},
        {1, 1, 3, 2},
        {1, 2, 3, 3},
        {2, 1, 3, 3}
    };
    if (n >= 4) {
        tests.emplace_back(1, 1, 1, 4);
        tests.emplace_back(1, 1, 4, 1);
        tests.emplace_back(1, 2, 2, 4);
        tests.emplace_back(2, 1, 4, 1);
    }
    // exists_pal lambda
    auto exists_pall = [&](const vector<vector<int>>& g, int x1, int y1, int x2, int y2) -> bool {
        int dx = x2 - x1, dy = y2 - y1;
        int total_moves = dx + dy;
        if (total_moves < 2) return false;
        vector<int> pathh;
        function<bool(int, int, int, int)> dfss = [&](int cx, int cy, int remd, int remr) -> bool {
            pathh.push_back(g[cx][cy]);
            if (remd == 0 && remr == 0) {
                int lenn = pathh.size();
                bool okk = true;
                for (int iii = 0; iii < lenn / 2; iii++) {
                    if (pathh[iii] != pathh[lenn - 1 - iii]) {
                        okk = false;
                        break;
                    }
                }
                pathh.pop_back();
                return okk;
            }
            bool ffound = false;
            if (remr > 0) {
                ffound = dfss(cx, cy + 1, remd, remr - 1);
                if (ffound) {
                    pathh.pop_back();
                    return true;
                }
            }
            if (remd > 0) {
                ffound = dfss(cx + 1, cy, remd - 1, remr);
                if (ffound) {
                    pathh.pop_back();
                    return true;
                }
            }
            pathh.pop_back();
            return false;
        };
        return dfss(x1, y1, dx, dy);
    };
    bool resolvedd = false;
    for (auto& tttp : tests) {
        int x1, y1, x2, y2;
        tie(x1, y1, x2, y2) = tttp;
        if (x2 > n || y2 > n) continue;
        int ddd = (x2 - x1) + (y2 - y1);
        if (ddd % 2 == 0 || ddd < 3) continue;
        bool r11 = exists_pall(grid, x1, y1, x2, y2);
        bool r22 = exists_pall(grid2, x1, y1, x2, y2);
        if (r11 != r22) {
            cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
            cout.flush();
            int realrr;
            cin >> realrr;
            if (realrr == -1) exit(0);
            if (realrr != r11) {
                for (int k = 0; k < mm; k++) {
                    auto [iii, jjj] = odd_list[k];
                    grid[iii][jjj] = 1 - grid[iii][jjj];
                }
            }
            resolvedd = true;
            break;
        }
    }
    assert(resolvedd);
    // output
    cout << "!" << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    cout.flush();
    return 0;
}