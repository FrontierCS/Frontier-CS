#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> g(n);
    for (int i = 0; i < n; i++) {
        cin >> g[i];
    }
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;
    pair<int, int> S_pos = {sr, sc};
    pair<int, int> E_pos = {er, ec};
    if (g[sr][sc] == '0' || g[er][ec] == '0') {
        cout << -1 << endl;
        return 0;
    }

    // Collect blank cells
    vector<pair<int, int>> cells;
    vector<vector<int>> id(n, vector<int>(m, -1));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (g[i][j] == '1') {
                id[i][j] = cells.size();
                cells.emplace_back(i, j);
            }
        }
    }
    int V = cells.size();
    if (V == 0) {
        cout << -1 << endl;
        return 0;
    }
    int sid = id[sr][sc];
    int eid = id[er][ec];

    // Check connected and build spanning tree
    vector<int> parent(V, -1);
    vector<bool> vis(V, false);
    queue<int> qq;
    qq.push(sid);
    vis[sid] = true;
    int visited_count = 1;
    while (!qq.empty()) {
        int u = qq.front(); qq.pop();
        auto [x, y] = cells[u];
        int dx[4] = {-1, 1, 0, 0};
        int dy[4] = {0, 0, -1, 1};
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && g[nx][ny] == '1') {
                int v = id[nx][ny];
                if (!vis[v]) {
                    vis[v] = true;
                    parent[v] = u;
                    qq.push(v);
                    visited_count++;
                }
            }
        }
    }
    if (visited_count < V) {
        cout << -1 << endl;
        return 0;
    }

    // Build tree
    vector<vector<int>> tree(V);
    for (int v = 0; v < V; v++) {
        if (parent[v] != -1) {
            tree[parent[v]].push_back(v);
        }
    }

    // DFS to build Q
    string Q = "";
    function<void(int, int)> dfs = [&](int u, int par) {
        for (int v : tree[u]) {
            if (v == par) continue;
            auto [ux, uy] = cells[u];
            auto [vx, vy] = cells[v];
            char to_dir;
            if (vx == ux && vy == uy + 1) to_dir = 'R';
            else if (vx == ux && vy == uy - 1) to_dir = 'L';
            else if (vx == ux + 1 && vy == uy) to_dir = 'D';
            else to_dir = 'U';
            Q += to_dir;
            dfs(v, u);
            char back_dir;
            if (to_dir == 'R') back_dir = 'L';
            else if (to_dir == 'L') back_dir = 'R';
            else if (to_dir == 'D') back_dir = 'U';
            else back_dir = 'D';
            Q += back_dir;
        }
    };
    dfs(sid, -1);

    // Compute revQ
    string revQ = Q;
    reverse(revQ.begin(), revQ.end());

    // Simulate function
    auto simulate_pos = [&](const string& moves, pair<int, int> pos) -> pair<int, int> {
        int r = pos.first, c = pos.second;
        for (char d : moves) {
            int nr = r, nc = c;
            if (d == 'U') nr--;
            else if (d == 'D') nr++;
            else if (d == 'L') nc--;
            else if (d == 'R') nc++;
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && g[nr][nc] == '1') {
                r = nr;
                c = nc;
            }
        }
        return {r, c};
    };

    pair<int, int> Y_pos = simulate_pos(revQ, S_pos);

    string ans;
    if (Y_pos == E_pos) {
        ans = Q + revQ;
    } else {
        // Product BFS
        const int MAXN = 30;
        vector<int> dist_flat(MAXN * MAXN * MAXN * MAXN, -1);
        auto get_idx = [&](int r1, int c1, int r2, int c2) -> int {
            return (((r1 * m + c1) * n + r2) * m + c2);
        };
        queue<tuple<int, int, int, int>> qqq;
        int Yr = Y_pos.first, Yc = Y_pos.second;
        int Sr_ = S_pos.first, Sc_ = S_pos.second;
        int init_idx = get_idx(Yr, Yc, Sr_, Sc_);
        dist_flat[init_idx] = 0;
        qqq.emplace(Yr, Yc, Sr_, Sc_);
        unordered_map<long long, pair<long long, char>> par_map;
        unordered_map<long long, string> seq_map;
        seq_map[init_idx] = "";
        bool found = false;
        tuple<int, int, int, int> goal_state;
        int goal_d = -1;
        int ddx[4] = {-1, 1, 0, 0};
        int ddy[4] = {0, 0, -1, 1};
        char dch[4] = {'U', 'D', 'L', 'R'};
        while (!qqq.empty() && !found) {
            auto [fr, fc, rr, rc] = qqq.front(); qqq.pop();
            int cidx = get_idx(fr, fc, rr, rc);
            int cd = dist_flat[cidx];
            if (fr == er && fc == ec && rr == sr && rc == sc) {
                found = true;
                goal_state = {fr, fc, rr, rc};
                goal_d = cd;
                break;
            }
            if (cd > 10000) continue;  // safety
            string old_seq = seq_map[cidx];
            int k = old_seq.size();
            for (int di = 0; di < 4; di++) {
                char ch = dch[di];
                // new F
                int nfr = fr + ddx[di];
                int nfc = fc + ddy[di];
                bool ok = (nfr >= 0 && nfr < n && nfc >= 0 && nfc < m && g[nfr][nfc] == '1');
                int new_fr = ok ? nfr : fr;
                int new_fc = ok ? nfc : fc;
                // new R: temp = target(ch, S_pos)
                int tr = sr, tc = sc;
                int tnr = tr + ddx[di];
                int tnc = tc + ddy[di];
                bool tok = (tnr >= 0 && tnr < n && tnc >= 0 && tnc < m && g[tnr][tnc] == '1');
                int temp_r = tok ? tnr : tr;
                int temp_c = tok ? tnc : tc;
                // now execute old reverse from temp
                int crr = temp_r, crc = temp_c;
                for (int t = k; t >= 1; t--) {
                    char move = old_seq[t - 1];
                    int mdi;
                    if (move == 'U') mdi = 0;
                    else if (move == 'D') mdi = 1;
                    else if (move == 'L') mdi = 2;
                    else mdi = 3;
                    int nnr = crr + ddx[mdi];
                    int nnc = crc + ddy[mdi];
                    bool mok = (nnr >= 0 && nnr < n && nnc >= 0 && nnc < m && g[nnr][nnc] == '1');
                    crr = mok ? nnr : crr;
                    crc = mok ? nnc : crc;
                }
                int new_rr = crr;
                int new_rc = crc;
                int nidx = get_idx(new_fr, new_fc, new_rr, new_rc);
                if (dist_flat[nidx] == -1) {
                    dist_flat[nidx] = cd + 1;
                    long long ccode = cidx;
                    long long ncode = nidx;
                    par_map[ncode] = {ccode, ch};
                    string nseq = old_seq + ch;
                    seq_map[ncode] = nseq;
                    qqq.emplace(new_fr, new_fc, new_rr, new_rc);
                    if (new_fr == er && new_fc == ec && new_rr == sr && new_rc == sc) {
                        found = true;
                        goal_state = {new_fr, new_fc, new_rr, new_rc};
                        goal_d = cd + 1;
                        break;
                    }
                }
            }
            if (found) break;
        }
        if (!found) {
            cout << -1 << endl;
            return 0;
        }
        // Reconstruct U
        string tempU = "";
        long long code = get_idx(get<0>(goal_state), get<1>(goal_state), get<2>(goal_state), get<3>(goal_state));
        int dd = goal_d;
        while (dd > 0) {
            auto p = par_map[code];
            tempU += p.second;
            code = p.first;
            dd--;
        }
        reverse(tempU.begin(), tempU.end());
        string U = tempU;
        string rev_U = U;
        reverse(rev_U.begin(), rev_U.end());
        string Q_new = rev_U + Q;
        string rev_Q_new = revQ + U;
        ans = Q_new + rev_Q_new;
    }

    // Verify (optional, but to be safe)
    auto final_pos = simulate_pos(ans, S_pos);
    if (final_pos != E_pos) {
        cout << -1 << endl;
        return 0;
    }
    // Check visits all (simulate visited)
    set<pair<int, int>> vis_all;
    pair<int, int> pos = S_pos;
    vis_all.insert(pos);
    for (char d : ans) {
        pos = target(pos, d);
        vis_all.insert(pos);
    }
    if (vis_all.size() < (size_t)V) {
        cout << -1 << endl;
        return 0;
    }

    if (ans.empty()) {
        cout << endl;
    } else {
        cout << ans << endl;
    }
    return 0;
}

pair<int, int> target(pair<int, int> p, char d) {
    int r = p.first, c = p.second;
    int nr = r, nc = c;
    if (d == 'U') nr--;
    else if (d == 'D') nr++;
    else if (d == 'L') nc--;
    else if (d == 'R') nc++;
    extern int n, m;  // assume global or pass
    // Wait, n m need to be accessible, assume in scope
    if (nr >= 0 && nr < n && nc >= 0 && nc < m) {
        extern vector<string> g;
        if (g[nr][nc] == '1') return {nr, nc};
    }
    return {r, c};
}