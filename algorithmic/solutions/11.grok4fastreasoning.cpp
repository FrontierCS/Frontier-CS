#include <bits/stdc++.h>
using namespace std;

int dr[4] = {0, 1, 0, -1};
int dc[4] = {1, 0, -1, 0};
char dirs[4] = {'R', 'D', 'L', 'U'};
int opp[4] = {2, 3, 0, 1};

int get_didx(char ch) {
    if (ch == 'R') return 0;
    if (ch == 'D') return 1;
    if (ch == 'L') return 2;
    return 3;
}

void dfs(int r, int c, int pr, int pc, const vector<int>& perm, vector<vector<bool>>& vis_dfs,
         vector<vector<vector<pair<int, int>>>>& children, const vector<string>& grid, int n, int m) {
    vis_dfs[r][c] = true;
    for (int i : perm) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !vis_dfs[nr][nc]) {
            children[r][c].push_back({nr, nc});
            dfs(nr, nc, r, c, perm, vis_dfs, children, grid, n, m);
        }
    }
}

string get_tour(int r, int c, const vector<vector<vector<pair<int, int>>>>& children, int n, int m,
                const vector<string>& grid) {
    string s = "";
    for (auto chld : children[r][c]) {
        int nr = chld.first, nc = chld.second;
        int d_idx = -1;
        for (int k = 0; k < 4; ++k) {
            if (r + dr[k] == nr && c + dc[k] == nc) {
                d_idx = k;
                break;
            }
        }
        assert(d_idx != -1);
        char move_to = dirs[d_idx];
        char move_back = dirs[opp[d_idx]];
        s += move_to;
        s += get_tour(nr, nc, children, n, m, grid);
        s += move_back;
    }
    return s;
}

pair<int, int> get_final_pos(const string& seq, int startr, int startc, int n, int m, const vector<string>& grid) {
    int cr = startr, cc = startc;
    for (char ch : seq) {
        int d_idx = get_didx(ch);
        int nr = cr + dr[d_idx];
        int nc = cc + dc[d_idx];
        if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
            cr = nr;
            cc = nc;
        }
    }
    return {cr, cc};
}

int get_visited_count(const string& seq, int startr, int startc, int n, int m, const vector<string>& grid) {
    vector<vector<bool>> simvis(n, vector<bool>(m, false));
    int cr = startr, cc = startc;
    simvis[cr][cc] = true;
    int cnt = 1;
    for (char ch : seq) {
        int d_idx = get_didx(ch);
        int nr = cr + dr[d_idx];
        int nc = cc + dc[d_idx];
        if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
            cr = nr;
            cc = nc;
        }
        if (!simvis[cr][cc]) {
            simvis[cr][cc] = true;
            cnt++;
        }
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    cin >> n >> m;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    int srow = sr - 1, scol = sc - 1, erow = er - 1, ecol = ec - 1;

    int total_blank = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == '1') total_blank++;
        }
    }

    // Check connectivity
    vector<vector<bool>> vis_conn(n, vector<bool>(m, false));
    queue<pair<int, int>> q;
    q.push({srow, scol});
    vis_conn[srow][scol] = true;
    int reached = 1;
    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !vis_conn[nr][nc]) {
                vis_conn[nr][nc] = true;
                reached++;
                q.push({nr, nc});
            }
        }
    }
    if (reached < total_blank || !vis_conn[erow][ecol]) {
        cout << -1 << endl;
        return 0;
    }

    // Now try all permutations
    vector<int> perm = {0, 1, 2, 3};
    bool found = false;
    string ans;
    do {
        vector<vector<bool>> vis_dfs(n, vector<bool>(m, false));
        vector<vector<vector<pair<int, int>>>> children(n, vector<vector<pair<int, int>>>(m));
        dfs(erow, ecol, -1, -1, perm, vis_dfs, children, grid, n, m);
        string RR = get_tour(erow, ecol, children, n, m, grid);
        string first_half = RR;
        reverse(first_half.begin(), first_half.end());
        int vcnt = get_visited_count(first_half, srow, scol, n, m, grid);
        if (vcnt == total_blank) {
            auto [xr, xc] = get_final_pos(first_half, srow, scol, n, m, grid);
            auto [yr, yc] = get_final_pos(RR, xr, xc, n, m, grid);
            if (yr == erow && yc == ecol) {
                ans = first_half + RR;
                found = true;
                break;
            }
        }
    } while (next_permutation(perm.begin(), perm.end()));

    if (found) {
        cout << ans << endl;
    } else {
        cout << -1 << endl;
    }
    return 0;
}