#include <bits/stdc++.h>
using namespace std;

const int MAXN = 30;
const int dx[4] = {0, 0, -1, 1};
const char move_char[4] = {'L', 'R', 'U', 'D'};
int n, m;
string grid[MAXN];
int sr, sc, er, ec;
int blank_count = 0;
int blank_id[MAXN][MAXN];
vector<pair<int,int>> blank_cells;

bool in_bounds(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= m;
}

bool is_blank(int r, int c) {
    return grid[r-1][c-1] == '1';
}

pair<int,int> simulate(int r, int c, int mi) {
    int nr = r + dx[mi] * (move_char[mi]=='U'? -1 : move_char[mi]=='D'? 1 : 0);
    int nc = c + (move_char[mi]=='L'? -1 : move_char[mi]=='R'? 1 : 0);
    if (in_bounds(nr, nc) && is_blank(nr, nc)) {
        return {nr, nc};
    } else {
        return {r, c};
    }
}

bool check_connectivity() {
    vector<vector<bool>> visited(n+1, vector<bool>(m+1, false));
    queue<pair<int,int>> q;
    q.push({sr, sc});
    visited[sr][sc] = true;
    int reached = 1;
    while (!q.empty()) {
        auto [r,c] = q.front(); q.pop();
        for (int mi = 0; mi < 4; mi++) {
            auto [nr, nc] = simulate(r, c, mi);
            if (!visited[nr][nc] && is_blank(nr, nc)) {
                visited[nr][nc] = true;
                reached++;
                q.push({nr, nc});
            }
        }
    }
    return reached == blank_count;
}

struct State {
    short lr, lc;
    short rr, rc;
    unsigned long long visited;
    int prev_state;
    char move;
    State(int lr=0, int lc=0, int rr=0, int rc=0, unsigned long long visited=0, int prev_state=-1, char move=0)
        : lr(lr), lc(lc), rr(rr), rc(rc), visited(visited), prev_state(prev_state), move(move) {}
};

string solve_small() {
    memset(blank_id, -1, sizeof blank_id);
    blank_cells.clear();
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (is_blank(i, j)) {
                blank_id[i][j] = blank_cells.size();
                blank_cells.push_back({i,j});
            }
        }
    }
    int start_mask = (1ULL << blank_id[sr][sc]) | (1ULL << blank_id[er][ec]);
    queue<State> q;
    map<tuple<int,int,int,int,unsigned long long>, bool> seen;
    State start(sr, sc, er, ec, start_mask, -1, 0);
    q.push(start);
    seen[{sr, sc, er, ec, start_mask}] = true;
    vector<State> states; states.push_back(start);
    int goal_index = -1;
    while (!q.empty()) {
        State cur = q.front(); q.pop();
        int cur_idx = states.size() - 1;
        if (cur.visited == (1ULL << blank_count) - 1) {
            if (cur.lr == cur.rr && cur.lc == cur.rc) {
                goal_index = cur_idx;
                break;
            }
            for (int mi = 0; mi < 4; mi++) {
                auto [nlr, nlc] = simulate(cur.lr, cur.lc, mi);
                if (nlr == cur.rr && nlc == cur.rc) {
                    State next = cur;
                    next.lr = nlr; next.lc = nlc;
                    next.prev_state = cur_idx;
                    next.move = move_char[mi];
                    states.push_back(next);
                    goal_index = states.size() - 1;
                    goto found;
                }
            }
        }
        for (int mi = 0; mi < 4; mi++) {
            auto [nlr, nlc] = simulate(cur.lr, cur.lc, mi);
            vector<pair<int,int>> possible_R;
            int opp_mi;
            if (move_char[mi] == 'L') opp_mi = 1;
            else if (move_char[mi] == 'R') opp_mi = 0;
            else if (move_char[mi] == 'U') opp_mi = 3;
            else opp_mi = 2;
            auto [pr, pc] = simulate(cur.rr, cur.rc, opp_mi);
            if (pr != cur.rr || pc != cur.rc) {
                possible_R.push_back({pr, pc});
            }
            auto [tr, tc] = simulate(cur.rr, cur.rc, mi);
            if (tr == cur.rr && tc == cur.rc) {
                possible_R.push_back({cur.rr, cur.rc});
            }
            for (auto [nrr, nrc] : possible_R) {
                unsigned long long new_visited = cur.visited;
                int id1 = blank_id[nlr][nlc];
                if (id1 != -1) new_visited |= (1ULL << id1);
                int id2 = blank_id[nrr][nrc];
                if (id2 != -1) new_visited |= (1ULL << id2);
                auto key = make_tuple(nlr, nlc, nrr, nrc, new_visited);
                if (!seen[key]) {
                    seen[key] = true;
                    State next(nlr, nlc, nrr, nrc, new_visited, cur_idx, move_char[mi]);
                    states.push_back(next);
                    q.push(next);
                }
            }
        }
    }
found:
    if (goal_index == -1) {
        return "-1";
    }
    string seq = "";
    State cur = states[goal_index];
    bool odd = (cur.lr == cur.rr && cur.lc == cur.rc) ? false : true;
    if (odd) {
        seq += cur.move;
        cur = states[cur.prev_state];
    }
    string A = "";
    while (cur.prev_state != -1) {
        A += cur.move;
        cur = states[cur.prev_state];
    }
    reverse(A.begin(), A.end());
    string revA = A;
    reverse(revA.begin(), revA.end());
    if (odd) {
        return A + seq + revA;
    } else {
        return A + revA;
    }
}

string solve_large() {
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (!is_blank(i, j)) {
                return "-1";
            }
        }
    }
    vector<vector<bool>> vis(n+1, vector<bool>(m+1, false));
    int dir = 0;
    string spiral = "";
    int r = sr, c = sc;
    vis[r][c] = true;
    int visited_count = 1;
    while (visited_count < n*m) {
        int nr = r, nc = c;
        if (dir == 0) nc = c+1;
        else if (dir == 1) nr = r+1;
        else if (dir == 2) nc = c-1;
        else nr = r-1;
        if (in_bounds(nr, nc) && !vis[nr][nc]) {
            char mchar;
            if (dir == 0) mchar = 'R';
            else if (dir == 1) mchar = 'D';
            else if (dir == 2) mchar = 'L';
            else mchar = 'U';
            spiral += mchar;
            r = nr; c = nc;
            vis[r][c] = true;
            visited_count++;
            int next_dir = (dir + 1) % 4;
            int nr2 = r, nc2 = c;
            if (next_dir == 0) nc2 = c+1;
            else if (next_dir == 1) nr2 = r+1;
            else if (next_dir == 2) nc2 = c-1;
            else nr2 = r-1;
            if (in_bounds(nr2, nc2) && !vis[nr2][nc2]) {
                dir = next_dir;
            }
        } else {
            dir = (dir + 1) % 4;
        }
    }
    int pr = sr, pc = sc;
    for (char ch : spiral) {
        int mi;
        if (ch == 'L') mi = 0;
        else if (ch == 'R') mi = 1;
        else if (ch == 'U') mi = 2;
        else mi = 3;
        auto [nr, nc] = simulate(pr, pc, mi);
        pr = nr; pc = nc;
    }
    string rev_spiral = spiral;
    reverse(rev_spiral.begin(), rev_spiral.end());
    int qr = pr, qc = pc;
    for (char ch : rev_spiral) {
        int mi;
        if (ch == 'L') mi = 0;
        else if (ch == 'R') mi = 1;
        else if (ch == 'U') mi = 2;
        else mi = 3;
        auto [nr, nc] = simulate(qr, qc, mi);
        qr = nr; qc = nc;
    }
    if (qr == er && qc == ec) {
        return spiral + rev_spiral;
    } else {
        return "-1";
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m;
    for (int i = 0; i < n; i++) {
        cin >> grid[i];
    }
    cin >> sr >> sc >> er >> ec;
    blank_count = 0;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (is_blank(i, j)) blank_count++;
        }
    }
    if (!check_connectivity()) {
        cout << "-1\n";
        return 0;
    }
    if (blank_count <= 15) {
        string ans = solve_small();
        cout << ans << "\n";
    } else {
        string ans = solve_large();
        cout << ans << "\n";
    }
    return 0;
}