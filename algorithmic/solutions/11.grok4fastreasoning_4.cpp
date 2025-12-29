#include <bits/stdc++.h>
using namespace std;

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

    // Count total blank
    int total_blank = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (grid[i][j] == '1') total_blank++;
        }
    }

    // Directions
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char movec[4] = {'U', 'D', 'L', 'R'};
    char opp[4] = {'D', 'U', 'R', 'L'};

    auto get_dir = [&](char c) -> int {
        if (c == 'U') return 0;
        if (c == 'D') return 1;
        if (c == 'L') return 2;
        if (c == 'R') return 3;
        return -1;
    };

    // BFS for connected and parent
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(m, {-1, -1}));
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vis[sr][sc] = true;
    int reached = 1;
    parent[sr][sc] = {-2, -2}; // sentinel
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && grid[nx][ny] == '1' && !vis[nx][ny]) {
                vis[nx][ny] = true;
                parent[nx][ny] = {x, y};
                q.push({nx, ny});
                reached++;
            }
        }
    }
    if (reached < total_blank || !vis[er][ec]) {
        cout << -1 << endl;
        return 0;
    }

    // Build path from S to E
    vector<pair<int, int>> pathh;
    int curx = er, cury = ec;
    while (true) {
        pathh.emplace_back(curx, cury);
        if (curx == sr && cury == sc) break;
        auto pr = parent[curx][cury];
        curx = pr.first;
        cury = pr.second;
    }
    reverse(pathh.begin(), pathh.end());

    // on_path
    set<pair<int, int>> on_pathh;
    for (auto p : pathh) on_pathh.insert(p);

    // next_on_path
    vector<vector<pair<int, int>>> next_on(n, vector<pair<int, int>>(m, {-1, -1}));
    for (size_t i = 0; i + 1 < pathh.size(); i++) {
        next_on[ pathh[i].first ][ pathh[i].second ] = pathh[i + 1];
    }

    // Recursive get_traversal
    function<string(int, int)> get_trav = [&](int x, int y) -> string {
        string seqq = "";
        vector<pair<int, int>> childr;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < m; j++) {
                if (grid[i][j] == '1' && parent[i][j] == make_pair(x, y)) {
                    childr.emplace_back(i, j);
                }
            }
        }
        pair<int, int> contc = {-1, -1};
        bool hasc = on_pathh.count({x, y}) && (x != er || y != ec);
        if (hasc) {
            contc = next_on[x][y];
        }
        vector<pair<int, int>> tv;
        for (auto ch : childr) {
            if (ch != contc) tv.push_back(ch);
        }
        if (hasc) tv.push_back(contc);
        for (auto ch : tv) {
            int cx = ch.first, cy = ch.second;
            int delxx = cx - x, del yy = cy - y;
            int dd = -1;
            if (delxx == -1 && del yy == 0) dd = 0;
            else if (delxx == 1 && del yy == 0) dd = 1;
            else if (delxx == 0 && del yy == -1) dd = 2;
            else if (delxx == 0 && del yy == 1) dd = 3;
            char mt = movec[dd];
            char mb = opp[dd];
            string su = get_trav(cx, cy);
            seqq += mt;
            seqq += su;
            bool chc = on_pathh.count(ch);
            if (!chc) {
                seqq += mb;
            }
        }
        return seqq;
    };

    string P = get_trav(sr, sc);

    // Now compute revP
    string revP = P;
    reverse(revP.begin(), revP.end());

    // Simulate executing revP from er,ec to get G
    int cx = er, cy = ec;
    for (char mm : revP) {
        int nd = get_dir(mm);
        if (nd == -1) continue; // error
        int nx = cx + dx[nd], ny = cy + dy[nd];
        if (nx >= 0 && nx < n && ny >= 0 && ny < m && grid[nx][ny] == '1') {
            cx = nx;
            cy = ny;
        }
    }
    int Gx = cx, Gy = cy;

    string full;
    if (Gx == er && Gy == ec) {
        full = P + revP;
    } else {
        // BFS for U
        const int MAX_ST = 4000;
        int NN = n * m;
        int strd = MAX_ST + 1;
        vector<int> pr_id(NN * strd, -1);
        vector<int> pr_st(NN * strd, -1);
        vector<char> pr_mvv(NN * strd, 0);
        vector<char> vstd(NN * strd, 0);
        queue<pair<int, int>> qq;
        int g_id = Gx * m + Gy;
        int ee_id = er * m + ec;
        int ss_id = sr * m + sc; // not used directly
        qq.push({g_id, 0});
        int sidx = g_id * strd + 0;
        vstd[sidx] = 1;
        bool fnd = false;
        string ufound;
        int found_st = -1;
        int found_pid = -1;
        while (!qq.empty() && !fnd) {
            auto [pid, st] = qq.front(); qq.pop();
            int px = pid / m, py = pid % m;
            if (px == er && py == ec) {
                // reconstruct
                string temp;
                int tcpid = pid, tcst = st;
                while (tcst > 0) {
                    int tcidx = tcpid * strd + tcst;
                    temp += pr_mvv[tcidx];
                    int tppid = pr_id[tcidx];
                    int tpst = pr_st[tcidx];
                    tcpid = tppid;
                    tcst = tpst;
                }
                reverse(temp.begin(), temp.end());
                // simulate rev
                int ttx = sr, tty = sc;
                for (int ii = (int)temp.size() - 1; ii >= 0; ii--) {
                    char mm = temp[ii];
                    int nd = get_dir(mm);
                    int nnx = ttx + dx[nd], nny = tty + dy[nd];
                    if (nnx >= 0 && nnx < n && nny >= 0 && nny < m && grid[nnx][nny] == '1') {
                        ttx = nnx;
                        tty = nny;
                    }
                }
                if (ttx == sr && tty == sc) {
                    fnd = true;
                    ufound = temp;
                    found_st = st;
                    found_pid = pid;
                    // continue to empty queue? No, since we want any, we can break
                    // but to find shortest, since BFS, first one is shortest
                    // so we can set fnd and break the loop
                    qq = queue<pair<int,int>>(); // clear queue to exit while
                    break;
                }
            }
            int nstt = st + 1;
            if (nstt > MAX_ST) continue;
            for (int dd = 0; dd < 4; dd++) {
                char mm = movec[dd];
                int nx = px + dx[dd], ny = py + dy[dd];
                int npxx = px, npyy = py;
                if (nx >= 0 && nx < n && ny >= 0 && ny < m && grid[nx][ny] == '1') {
                    npxx = nx;
                    npyy = ny;
                }
                int npidd = npxx * m + npyy;
                int nidx = npidd * strd + nstt;
                if (vstd[nidx]) continue;
                vstd[nidx] = 1;
                qq.push({npidd, nstt});
                int oidx = pid * strd + st;
                pr_id[nidx] = pid;
                pr_st[nidx] = st;
                pr_mvv[nidx] = mm;
            }
        }
        if (!fnd) {
            cout << -1 << endl;
            return 0;
        }
        string U = ufound;
        string rev_U = U;
        reverse(rev_U.begin(), rev_U.end());
        full = rev_U + P + revP + U;
    }

    // Output
    if (full.empty()) {
        cout << endl;
    } else {
        cout << full << endl;
    }
    return 0;
}