#include <bits/stdc++.h>
using namespace std;

char flipc(char c) {
    if (c == 'L') return 'R';
    if (c == 'R') return 'L';
    if (c == 'U') return 'D';
    if (c == 'D') return 'U';
    assert(false);
    return ' ';
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) {
        cin >> grid[i];
    }
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;
    int total = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (grid[i][j] == '1') total++;
        }
    }
    int start_id = sr * m + sc;
    vector<bool> vis(n * m, false);
    vector<int> par(n * m, -1);
    vector<vector<int>> children(n * m);
    queue<int> qq;
    qq.push(start_id);
    vis[start_id] = true;
    int reached = 1;
    int dr[4] = {0, 0, -1, 1};
    int dc[4] = {-1, 1, 0, 0};
    string dirchars = "LRUD";
    int opp[4] = {1, 0, 3, 2};
    while (!qq.empty()) {
        int u = qq.front();
        qq.pop();
        int ui = u / m, uj = u % m;
        for (int d = 0; d < 4; d++) {
            int vi = ui + dr[d], vj = uj + dc[d];
            if (vi < 0 || vi >= n || vj < 0 || vj >= m || grid[vi][vj] == '0' || vis[vi * m + vj]) continue;
            int v = vi * m + vj;
            vis[v] = true;
            qq.push(v);
            par[v] = u;
            children[u].push_back(v);
            reached++;
        }
    }
    if (reached < total) {
        cout << -1 << endl;
        return 0;
    }
    string P = "";
    auto dfs = [&](auto&& self, int u) -> void {
        for (int v : children[u]) {
            int ui = u / m, uj = u % m, vi = v / m, vj = v % m;
            int ddi = vi - ui, ddj = vj - uj;
            char move;
            if (ddi == 0 && ddj == -1) move = 'L';
            else if (ddi == 0 && ddj == 1) move = 'R';
            else if (ddi == -1 && ddj == 0) move = 'U';
            else if (ddi == 1 && ddj == 0) move = 'D';
            else assert(false);
            P += move;
            self(self, v);
            P += flipc(move);
        }
    };
    dfs(dfs, start_id);
    string revP = P;
    reverse(revP.begin(), revP.end());
    auto simulate = [&](const string& seq, int si, int sj) -> pair<int, int> {
        int r = si, c = sj;
        for (char ch : seq) {
            int nr = r, nc = c;
            if (ch == 'L') nc--;
            else if (ch == 'R') nc++;
            else if (ch == 'U') nr--;
            else if (ch == 'D') nr++;
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
                r = nr;
                c = nc;
            }
        }
        return {r, c};
    };
    auto endp = simulate(revP, sr, sc);
    int tx = er, ty = ec;
    if (endp.first == tx && endp.second == ty) {
        string full = P + revP;
        cout << full << endl;
        return 0;
    }
    int x_id = endp.first * m + endp.second;
    int s_id = sr * m + sc;
    int e_id = er * m + ec;
    vector<vector<bool>> visited(n * m, vector<bool>(n * m, false));
    vector<vector<pair<int, int>>> prev_st(n * m, vector<pair<int, int>>(n * m, {-1, -1}));
    vector<vector<char>> used_m(n * m, vector<char>(n * m, ' '));
    queue<pair<int, int>> qb;
    qb.push({x_id, s_id});
    visited[x_id][s_id] = true;
    prev_st[x_id][s_id] = {-2, -2};
    used_m[x_id][s_id] = ' ';
    bool found = (x_id == e_id && s_id == s_id);
    while (!qb.empty() && !found) {
        auto [pf, pr] = qb.front();
        qb.pop();
        if (pf == e_id && pr == s_id) {
            found = true;
            continue;
        }
        int pfi = pf / m, pfj = pf % m;
        int pri = pr / m, prj = pr % m;
        for (int d = 0; d < 4; d++) {
            char ch = dirchars[d];
            int nri = pfi + dr[d], nrj = pfj + dc[d];
            int npf = pf;
            if (nri >= 0 && nri < n && nrj >= 0 && nrj < m && grid[nri][nrj] == '1') {
                npf = nri * m + nrj;
            }
            int op = opp[d];
            int predi = pri + dr[op], predj = prj + dc[op];
            vector<int> cands;
            if (predi >= 0 && predi < n && predj >= 0 && predj < m && grid[predi][predj] == '1') {
                cands.push_back(predi * m + predj);
            }
            int sri = pri + dr[d], srj = prj + dc[d];
            bool stay_ok = !(sri >= 0 && sri < n && srj >= 0 && srj < m && grid[sri][srj] == '1');
            if (stay_ok) {
                cands.push_back(pr);
            }
            for (int nrpr : cands) {
                if (!visited[npf][nrpr]) {
                    visited[npf][nrpr] = true;
                    qb.push({npf, nrpr});
                    prev_st[npf][nrpr] = {pf, pr};
                    used_m[npf][nrpr] = ch;
                    if (npf == e_id && nrpr == s_id) {
                        found = true;
                    }
                }
            }
        }
    }
    if (!visited[e_id][s_id]) {
        cout << -1 << endl;
        return 0;
    }
    string Tt = "";
    int cpf = e_id, cpr = s_id;
    vector<char> moves_rev;
    while (prev_st[cpf][cpr].first != -2) {
        char chh = used_m[cpf][cpr];
        moves_rev.push_back(chh);
        auto [ppf, ppr] = prev_st[cpf][cpr];
        cpf = ppf;
        cpr = ppr;
    }
    reverse(moves_rev.begin(), moves_rev.end());
    for (char c : moves_rev) Tt += c;
    string revTt = Tt;
    reverse(revTt.begin(), revTt.end());
    string full = revTt + P + revP + Tt;
    cout << full << endl;
    return 0;
}