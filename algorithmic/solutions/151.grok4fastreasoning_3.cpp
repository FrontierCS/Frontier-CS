#include <bits/stdc++.h>
using namespace std;

int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};
char dirs[4] = {'U', 'D', 'L', 'R'};

struct Edge {
    int u, v, w;
};

bool cmp(const Edge& a, const Edge& b) {
    return a.w < b.w;
}

vector<char> get_reverse(const vector<char>& m) {
    vector<char> rm;
    rm.reserve(m.size());
    for (auto it = m.rbegin(); it != m.rend(); ++it) {
        char c = *it;
        if (c == 'U') rm.push_back('D');
        else if (c == 'D') rm.push_back('U');
        else if (c == 'L') rm.push_back('R');
        else if (c == 'R') rm.push_back('L');
    }
    return rm;
}

void meta_dfs(int u, int par, const vector<vector<int>>& meta_adj, const vector<vector<vector<char>>>& sp_m, vector<char>& full_path) {
    for (int v : meta_adj[u]) {
        if (v == par) continue;
        const auto& go = sp_m[u][v];
        for (char c : go) full_path.push_back(c);
        meta_dfs(v, u, meta_adj, sp_m, full_path);
        auto backk = get_reverse(go);
        for (char c : backk) full_path.push_back(c);
    }
}

int main() {
    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];
    vector<pair<int, int>> v_int;
    for (int j = 0; j < N; j++) {
        int i = 0;
        while (i < N) {
            if (grid[i][j] == '#') {
                i++;
                continue;
            }
            int st = i;
            while (i < N && grid[i][j] != '#') i++;
            int en = i - 1;
            v_int.emplace_back(st, en);
        }
    }
    vector<pair<int, int>> h_int;
    for (int i = 0; i < N; i++) {
        int j = 0;
        while (j < N) {
            if (grid[i][j] == '#') {
                j++;
                continue;
            }
            int st = j;
            while (j < N && grid[i][j] != '#') j++;
            int en = j - 1;
            h_int.emplace_back(st, en);
        }
    }
    auto compute_chosen = [](vector<pair<int, int>> ints) -> vector<int> {
        vector<int> ch;
        while (!ints.empty()) {
            sort(ints.begin(), ints.end(), [](auto& a, auto& b) { return a.second < b.second; });
            int pt = ints[0].second;
            ch.push_back(pt);
            vector<pair<int, int>> nw;
            for (auto& p : ints) {
                if (p.first > pt || p.second < pt) nw.push_back(p);
            }
            ints = std::move(nw);
        }
        return ch;
    };
    vector<int> chosen_rows = compute_chosen(v_int);
    vector<int> chosen_cols = compute_chosen(h_int);
    int num_ur = 0;
    for (int rr : chosen_rows) {
        for (int j = 0; j < N; j++) if (grid[rr][j] != '#') num_ur++;
    }
    int num_uc = 0;
    for (int cc : chosen_cols) {
        for (int i = 0; i < N; i++) if (grid[i][cc] != '#') num_uc++;
    }
    bool use_row = (num_ur <= num_uc);
    vector<pair<int, int>> terms;
    int term_id[70][70];
    memset(term_id, -1, sizeof(term_id));
    int idx = 0;
    if (use_row) {
        for (int rr : chosen_rows) {
            for (int j = 0; j < N; j++) {
                if (grid[rr][j] != '#') {
                    terms.emplace_back(rr, j);
                    term_id[rr][j] = idx++;
                }
            }
        }
    } else {
        for (int cc : chosen_cols) {
            for (int i = 0; i < N; i++) {
                if (grid[i][cc] != '#') {
                    terms.emplace_back(i, cc);
                    term_id[i][cc] = idx++;
                }
            }
        }
    }
    bool has_start = (term_id[si][sj] != -1);
    if (!has_start) {
        terms.emplace_back(si, sj);
        term_id[si][sj] = idx++;
    }
    int kk = terms.size();
    int start_t = term_id[si][sj];
    const int INF = 1e9;
    vector<vector<int>> sp_d(kk, vector<int>(kk, INF));
    vector<vector<vector<char>>> sp_m(kk, vector<vector<char>>(kk));
    int ppi[70][70], ppj[70][70];
    int ddist[70][70];
    for (int a = 0; a < kk; a++) {
        int sx = terms[a].first, sy = terms[a].second;
        memset(ddist, -1, sizeof(ddist));
        ddist[sx][sy] = 0;
        memset(ppi, -1, sizeof(ppi));
        memset(ppj, -1, sizeof(ppj));
        queue<pair<int, int>> qq;
        qq.push({sx, sy});
        while (!qq.empty()) {
            auto [x, y] = qq.front();
            qq.pop();
            for (int d = 0; d < 4; d++) {
                int nx = x + dx[d], ny = y + dy[d];
                if (nx >= 0 && nx < N && ny >= 0 && ny < N && grid[nx][ny] != '#' && ddist[nx][ny] == -1) {
                    ddist[nx][ny] = ddist[x][y] + 1;
                    ppi[nx][ny] = x;
                    ppj[nx][ny] = y;
                    qq.push({nx, ny});
                }
            }
        }
        sp_d[a][a] = 0;
        for (int t = 0; t < kk; t++) {
            if (t == a) continue;
            int tx = terms[t].first, ty = terms[t].second;
            int dd = ddist[tx][ty];
            if (dd == -1) continue;
            sp_d[a][t] = dd;
            vector<pair<int, int>> posp;
            int curx = tx, cury = ty;
            while (curx != sx || cury != sy) {
                posp.emplace_back(curx, cury);
                int prevx = ppi[curx][cury];
                int prevy = ppj[curx][cury];
                curx = prevx;
                cury = prevy;
            }
            posp.emplace_back(sx, sy);
            reverse(posp.begin(), posp.end());
            vector<char> mm;
            for (size_t p = 0; p + 1 < posp.size(); ++p) {
                int cx = posp[p].first, cy = posp[p].second;
                int nx = posp[p + 1].first, ny = posp[p + 1].second;
                char md;
                if (nx == cx - 1 && ny == cy) md = 'U';
                else if (nx == cx + 1 && ny == cy) md = 'D';
                else if (nx == cx && ny == cy - 1) md = 'L';
                else if (nx == cx && ny == cy + 1) md = 'R';
                else assert(false);
                mm.push_back(md);
            }
            sp_m[a][t] = mm;
        }
    }
    vector<Edge> alledges;
    for (int i = 0; i < kk; i++) {
        for (int j = i + 1; j < kk; j++) {
            if (sp_d[i][j] < INF) {
                alledges.push_back({i, j, sp_d[i][j]});
            }
        }
    }
    sort(alledges.begin(), alledges.end(), cmp);
    vector<int> pr(kk);
    for (int i = 0; i < kk; i++) pr[i] = i;
    auto find = [&](auto& self, int x) -> int {
        return pr[x] == x ? x : pr[x] = self(self, pr[x]);
    };
    vector<vector<int>> meta_adj(kk);
    for (auto& e : alledges) {
        int fu = find(find, e.u), fv = find(find, e.v);
        if (fu != fv) {
            pr[fu] = fv;
            meta_adj[e.u].push_back(e.v);
            meta_adj[e.v].push_back(e.u);
        }
    }
    vector<char> full_path;
    meta_dfs(start_t, -1, meta_adj, sp_m, full_path);
    for (char c : full_path) cout << c;
    cout << endl;
    return 0;
}