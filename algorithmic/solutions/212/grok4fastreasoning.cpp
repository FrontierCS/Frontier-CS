#include <bits/stdc++.h>
using namespace std;

bool is_subseq(const vector<int>& p, const vector<int>& q) {
    size_t j = 0;
    for (int r : p) {
        if (j < q.size() && r == q[j]) j++;
    }
    return j == q.size();
}

int main() {
    int n, m, L, R, Sx, Sy, Lq, s;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    vector<int> q_vec(Lq);
    for (auto& x : q_vec) cin >> x;
    map<int, int> q_index;
    for (int i = 0; i < Lq; i++) {
        q_index[q_vec[i]] = i + 1;
    }
    bool possible = true;
    if (q_index.count(Sx) && q_index[Sx] != 1) possible = false;
    if (!possible) {
        cout << "NO" << endl;
        return 0;
    }
    vector<int> to_process_q;
    for (int i = 0; i < Lq; i++) {
        if (q_vec[i] != Sx) to_process_q.push_back(q_vec[i]);
    }
    vector<int> free_r;
    for (int i = 1; i <= n; i++) {
        if (i != Sx && q_index.find(i) == q_index.end()) free_r.push_back(i);
    }
    vector<vector<int>> possible_orders;
    // First: after q, free increasing
    {
        vector<int> free_copy = free_r;
        sort(free_copy.begin(), free_copy.end());
        vector<int> ord;
        ord.push_back(Sx);
        for (int r : to_process_q) ord.push_back(r);
        for (int r : free_copy) ord.push_back(r);
        possible_orders.push_back(ord);
    }
    // Second: after q, free decreasing
    {
        vector<int> free_copy = free_r;
        sort(free_copy.rbegin(), free_copy.rend());
        vector<int> ord;
        ord.push_back(Sx);
        for (int r : to_process_q) ord.push_back(r);
        for (int r : free_copy) ord.push_back(r);
        possible_orders.push_back(ord);
    }
    // Third: free before q, increasing
    {
        vector<int> free_copy = free_r;
        sort(free_copy.begin(), free_copy.end());
        vector<int> ord;
        ord.push_back(Sx);
        for (int r : free_copy) ord.push_back(r);
        for (int r : to_process_q) ord.push_back(r);
        possible_orders.push_back(ord);
    }
    // Snake1
    {
        vector<int> sn1;
        for (int r = Sx; r <= n; r++) sn1.push_back(r);
        for (int r = Sx - 1; r >= 1; r--) sn1.push_back(r);
        if (is_subseq(sn1, q_vec)) possible_orders.push_back(sn1);
    }
    // Snake2
    {
        vector<int> sn2;
        for (int r = Sx; r >= 1; r--) sn2.push_back(r);
        for (int r = Sx + 1; r <= n; r++) sn2.push_back(r);
        if (is_subseq(sn2, q_vec)) possible_orders.push_back(sn2);
    }
    // Snake1 reversed second block
    {
        vector<int> sn1r;
        for (int r = Sx; r <= n; r++) sn1r.push_back(r);
        for (int r = 1; r <= Sx - 1; r++) sn1r.push_back(r);
        if (is_subseq(sn1r, q_vec)) possible_orders.push_back(sn1r);
    }
    vector<vector<pair<int, int>>> candidate_paths;
    for (auto& ord : possible_orders) {
        vector<vector<bool>> vis(n + 2, vector<bool>(m + 2, false));
        vector<pair<int, int>> this_path;
        // Initial traversal
        for (int y = L; y <= R; y++) {
            this_path.push_back({Sx, y});
            vis[Sx][y] = true;
        }
        bool success = true;
        pair<int, int> curr_pos = {Sx, R};
        for (size_t idx = 1; idx < ord.size() && success; ++idx) {
            int next_r = ord[idx];
            set<int> unproc;
            for (size_t k = idx; k < ord.size(); ++k) unproc.insert(ord[k]);
            int cx = curr_pos.first, cy = curr_pos.second;
            // Find best entry
            int min_dist = INT_MAX;
            int best_e_col = -1;
            for (int e = 0; e < 2; e++) {
                int e_col = (e == 0 ? L : R);
                int tx = next_r, ty = e_col;
                // BFS
                vector<vector<int>> d(n + 2, vector<int>(m + 2, -1));
                vector<vector<pair<int, int>>> par(n + 2, vector<pair<int, int>>(m + 2, {-1, -1}));
                queue<pair<int, int>> qq;
                qq.push({cx, cy});
                d[cx][cy] = 0;
                par[cx][cy] = {-1, -1};
                while (!qq.empty()) {
                    auto [x, y] = qq.front(); qq.pop();
                    int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
                    for (auto& dd : dirs) {
                        int nx = x + dd[0], ny = y + dd[1];
                        if (nx < 1 || nx > n || ny < 1 || ny > m) continue;
                        if (d[nx][ny] != -1) continue;
                        bool allwd = !vis[nx][ny];
                        if (allwd && L <= ny && ny <= R && unproc.count(nx) && !(nx == tx && ny == ty)) allwd = false;
                        if (!allwd) continue;
                        d[nx][ny] = d[x][y] + 1;
                        par[nx][ny] = {x, y};
                        qq.push({nx, ny});
                    }
                }
                int this_d = d[tx][ty];
                if (this_d != -1 && this_d < min_dist) {
                    min_dist = this_d;
                    best_e_col = e_col;
                }
            }
            if (min_dist == INT_MAX) {
                success = false;
                continue;
            }
            // Now run BFS for best
            int entry_col = best_e_col;
            int tx = next_r, ty = entry_col;
            vector<vector<int>> d(n + 2, vector<int>(m + 2, -1));
            vector<vector<pair<int, int>>> par(n + 2, vector<pair<int, int>>(m + 2, {-1, -1}));
            queue<pair<int, int>> qq;
            qq.push({cx, cy});
            d[cx][cy] = 0;
            par[cx][cy] = {-1, -1};
            while (!qq.empty()) {
                auto [x, y] = qq.front(); qq.pop();
                int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
                for (auto& dd : dirs) {
                    int nx = x + dd[0], ny = y + dd[1];
                    if (nx < 1 || nx > n || ny < 1 || ny > m) continue;
                    if (d[nx][ny] != -1) continue;
                    bool allwd = !vis[nx][ny];
                    if (allwd && L <= ny && ny <= R && unproc.count(nx) && !(nx == tx && ny == ty)) allwd = false;
                    if (!allwd) continue;
                    d[nx][ny] = d[x][y] + 1;
                    par[nx][ny] = {x, y};
                    qq.push({nx, ny});
                }
            }
            // Reconstruct
            vector<pair<int, int>> connect_p;
            pair<int, int> curp = {tx, ty};
            while (curp != make_pair(cx, cy)) {
                connect_p.push_back(curp);
                curp = par[curp.first][curp.second];
            }
            reverse(connect_p.begin(), connect_p.end());
            // Append connect_p
            for (auto pp : connect_p) {
                this_path.push_back(pp);
                vis[pp.first][pp.second] = true;
            }
            // Append remaining traversal
            int exit_c;
            if (entry_col == L) {
                for (int y = L + 1; y <= R; y++) {
                    this_path.push_back({next_r, y});
                    vis[next_r][y] = true;
                }
                exit_c = R;
            } else {
                for (int y = R - 1; y >= L; y--) {
                    this_path.push_back({next_r, y});
                    vis[next_r][y] = true;
                }
                exit_c = L;
            }
            curr_pos = {next_r, exit_c};
        }
        if (success) {
            candidate_paths.push_back(this_path);
        }
    }
    if (candidate_paths.empty()) {
        cout << "NO" << endl;
    } else {
        auto best_it = min_element(candidate_paths.begin(), candidate_paths.end(),
            [](const vector<pair<int, int>>& a, const vector<pair<int, int>>& b) {
                return a.size() < b.size();
            });
        auto& best_p = *best_it;
        cout << "YES" << endl;
        cout << best_p.size() << endl;
        for (auto [x, y] : best_p) {
            cout << x << " " << y << endl;
        }
    }
    return 0;
}