#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <vector>

using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;
int total_blanks = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char moves[] = "UDLR";

inline int get_id(int r, int c) {
    return r * m + c;
}

inline pair<int, int> get_pos(int id) {
    return {id / m, id % m};
}

pair<int, int> next_pos(int r, int c, char move) {
    int move_idx = -1;
    if (move == 'U') move_idx = 0;
    else if (move == 'D') move_idx = 1;
    else if (move == 'L') move_idx = 2;
    else if (move == 'R') move_idx = 3;

    if (move_idx == -1) return {r, c};

    int nr = r + dr[move_idx];
    int nc = c + dc[move_idx];

    if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
        return {nr, nc};
    }
    return {r, c};
}

char rev_move(char move) {
    if (move == 'U') return 'D';
    if (move == 'D') return 'U';
    if (move == 'L') return 'R';
    if (move == 'R') return 'L';
    return '\0';
}

bool check_connectivity() {
    if (grid[sr][sc] == '0') return false;
    queue<pair<int, int>> q;
    q.push({sr, sc});
    vector<vector<bool>> visited(n, vector<bool>(m, false));
    visited[sr][sc] = true;
    int count = 1;
    
    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !visited[nr][nc]) {
                visited[nr][nc] = true;
                q.push({nr, nc});
                count++;
            }
        }
    }
    return count == total_blanks;
}

struct Candidate {
    int len;
    int id1, id2;
    char mid_move;
    bool operator<(const Candidate& other) const {
        return len < other.len;
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    grid.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == '1') {
                total_blanks++;
            }
        }
    }
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;

    if (!check_connectivity()) {
        cout << -1 << endl;
        return 0;
    }
    
    if (total_blanks == 1 && sr == er && sc == ec) {
        cout << "" << endl;
        return 0;
    }

    int N_CELLS = n * m;
    vector<vector<int>> dist(N_CELLS, vector<int>(N_CELLS, -1));
    vector<vector<pair<int, int>>> parent(N_CELLS, vector<pair<int,int>>(N_CELLS, {-1,-1}));
    vector<vector<char>> p_move(N_CELLS, vector<char>(N_CELLS, '\0'));

    queue<pair<int, int>> q;

    int start_id1 = get_id(sr, sc);
    int start_id2 = get_id(er, ec);

    dist[start_id1][start_id2] = 0;
    q.push({start_id1, start_id2});

    while (!q.empty()) {
        auto [id1, id2] = q.front();
        q.pop();

        auto [r1, c1] = get_pos(id1);
        auto [r2, c2] = get_pos(id2);

        for (char move : moves) {
            auto [nr1, nc1] = next_pos(r1, c1, move);
            char r_move = rev_move(move);
            auto [nr2, nc2] = next_pos(r2, c2, r_move);
            int nid1 = get_id(nr1, nc1);
            int nid2 = get_id(nr2, nc2);
            if (dist[nid1][nid2] == -1) {
                dist[nid1][nid2] = dist[id1][id2] + 1;
                parent[nid1][nid2] = {id1, id2};
                p_move[nid1][nid2] = move;
                q.push({nid1, nid2});
            }
        }
    }

    vector<Candidate> candidates;

    // Even length candidates
    for (int i = 0; i < N_CELLS; ++i) {
        if (dist[i][i] != -1) {
            candidates.push_back({2 * dist[i][i], i, i, '\0'});
        }
    }
    
    // Odd length candidates
    for (int r1 = 0; r1 < n; ++r1) {
        for (int c1 = 0; c1 < m; ++c1) {
            if (grid[r1][c1] == '0') continue;

            // Horizontal
            if (c1 + 2 < m && grid[r1][c1+1] == '1' && grid[r1][c1+2] == '1') {
                int id1 = get_id(r1, c1);
                int id2 = get_id(r1, c1+2);
                if (dist[id1][id2] != -1) {
                    candidates.push_back({2 * dist[id1][id2] + 1, id1, id2, 'R'});
                }
            }
            // Vertical
            if (r1 + 2 < n && grid[r1+1][c1] == '1' && grid[r1+2][c1] == '1') {
                int id1 = get_id(r1, c1);
                int id2 = get_id(r1+2, c1);
                if (dist[id1][id2] != -1) {
                    candidates.push_back({2 * dist[id1][id2] + 1, id1, id2, 'D'});
                }
            }
        }
    }
    
    sort(candidates.begin(), candidates.end());

    for (const auto& cand : candidates) {
        string prefix = "";
        int cur_id1 = cand.id1;
        int cur_id2 = cand.id2;
        while (cur_id1 != start_id1 || cur_id2 != start_id2) {
            char move = p_move[cur_id1][cur_id2];
            prefix += move;
            auto p = parent[cur_id1][cur_id2];
            cur_id1 = p.first;
            cur_id2 = p.second;
        }
        reverse(prefix.begin(), prefix.end());

        string S = prefix;
        if (cand.mid_move != '\0') {
            S += cand.mid_move;
        }
        string reversed_prefix = prefix;
        reverse(reversed_prefix.begin(), reversed_prefix.end());
        S += reversed_prefix;
        
        vector<vector<bool>> visited(n, vector<bool>(m, false));
        int cur_r = sr, cur_c = sc;
        visited[cur_r][cur_c] = true;
        int visited_count = 1;

        for (char move : S) {
            auto [nr, nc] = next_pos(cur_r, cur_c, move);
            cur_r = nr;
            cur_c = nc;
            if (!visited[cur_r][cur_c]) {
                visited[cur_r][cur_c] = true;
                visited_count++;
            }
        }

        if (visited_count == total_blanks && cur_r == er && cur_c == ec) {
            cout << S << endl;
            return 0;
        }
    }

    cout << -1 << endl;

    return 0;
}