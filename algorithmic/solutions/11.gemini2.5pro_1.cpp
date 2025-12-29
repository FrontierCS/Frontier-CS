#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <algorithm>

using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;
int total_blank_cells = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char moves[] = {'U', 'D', 'L', 'R'};
map<char, char> opposite_move_map = {{'U', 'D'}, {'D', 'U'}, {'L', 'R'}, {'R', 'L'}};
map<char, int> move_to_idx = {{'U', 0}, {'D', 1}, {'L', 2}, {'R', 3}};

pair<int, int> do_move(int r, int c, char move_char) {
    int move_idx = move_to_idx[move_char];
    int nr = r + dr[move_idx];
    int nc = c + dc[move_idx];
    if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
        return {nr, nc};
    }
    return {r, c};
}

bool check_and_print(string p, char middle_char, bool is_odd) {
    string s = p;
    if (is_odd) {
        s += middle_char;
    }
    string p_rev = p;
    reverse(p_rev.begin(), p_rev.end());
    s += p_rev;

    vector<vector<bool>> visited(n, vector<bool>(m, false));
    int r = sr, c = sc;
    int visited_count = 0;
    if(grid[r][c] == '1') {
        visited[r][c] = true;
        visited_count = 1;
    }

    for (char move : s) {
        pair<int, int> next_pos = do_move(r, c, move);
        r = next_pos.first;
        c = next_pos.second;
        if (grid[r][c] == '1' && !visited[r][c]) {
            visited[r][c] = true;
            visited_count++;
        }
    }

    if (visited_count == total_blank_cells && r == er && c == ec) {
        cout << s << endl;
        return true;
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    grid.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == '1') {
                total_blank_cells++;
            }
        }
    }
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    vector<vector<bool>> visited_conn(n, vector<bool>(m, false));
    queue<pair<int, int>> q_conn;
    int reachable_blank = 0;

    if (grid[sr][sc] == '1') {
        q_conn.push({sr, sc});
        visited_conn[sr][sc] = true;
        reachable_blank++;
    }

    while (!q_conn.empty()) {
        pair<int, int> curr = q_conn.front();
        q_conn.pop();

        for (int i = 0; i < 4; ++i) {
            int nr = curr.first + dr[i];
            int nc = curr.second + dc[i];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1' && !visited_conn[nr][nc]) {
                visited_conn[nr][nc] = true;
                q_conn.push({nr, nc});
                reachable_blank++;
            }
        }
    }

    if (reachable_blank != total_blank_cells) {
        cout << -1 << endl;
        return 0;
    }

    if (sr == er && sc == ec) {
        if (total_blank_cells == 1) {
            cout << "" << endl;
        } else {
             cout << -1 << endl;
        }
        return 0;
    }

    int NM = n * m;
    vector<vector<pair<int, int>>> parent(NM, vector<pair<int, int>>(NM, {-1, -1}));
    vector<vector<char>> move_char(NM, vector<char>(NM));

    queue<pair<int, int>> q;
    
    int start_p1 = sr * m + sc;
    int start_p2 = er * m + ec;

    q.push({start_p1, start_p2});
    parent[start_p1][start_p2] = {-2, -2};

    while (!q.empty()) {
        int level_size = q.size();
        vector<pair<int, int>> current_level_nodes;
        for (int i=0; i < level_size; ++i) {
            current_level_nodes.push_back(q.front());
            q.pop();
        }

        for (auto const& state : current_level_nodes) {
            int r1 = state.first / m, c1 = state.first % m;
            int r2 = state.second / m, c2 = state.second % m;
            for (int j = 0; j < 4; ++j) {
                char c_move = moves[j];
                pair<int, int> p1_moved = do_move(r1, c1, c_move);
                if (p1_moved.first == r2 && p1_moved.second == c2) {
                    string p = "";
                    pair<int, int> temp_curr = state;
                    while (parent[temp_curr.first][temp_curr.second].first != -2) {
                        p += move_char[temp_curr.first][temp_curr.second];
                        temp_curr = parent[temp_curr.first][temp_curr.second];
                    }
                    reverse(p.begin(), p.end());
                    if (check_and_print(p, c_move, true)) return 0;
                }
            }
        }
        
        vector<pair<int, int>> meeting_nodes;
        for(auto const& curr : current_level_nodes){
            int r1 = curr.first / m, c1 = curr.first % m;
            int r2 = curr.second / m, c2 = curr.second % m;
            
            for (int j = 0; j < 4; ++j) {
                char move_m = moves[j];
                pair<int, int> next_p1 = do_move(r1, c1, move_m);
                pair<int, int> next_p2 = do_move(r2, c2, opposite_move_map[move_m]);
                
                int next_p1_idx = next_p1.first * m + next_p1.second;
                int next_p2_idx = next_p2.first * m + next_p2.second;

                if (parent[next_p1_idx][next_p2_idx].first == -1) {
                    parent[next_p1_idx][next_p2_idx] = curr;
                    move_char[next_p1_idx][next_p2_idx] = move_m;
                    q.push({next_p1_idx, next_p2_idx});
                    if (next_p1_idx == next_p2_idx) {
                        meeting_nodes.push_back({next_p1_idx, next_p2_idx});
                    }
                }
            }
        }
        
        if (!meeting_nodes.empty()) {
            for (auto const& meeting_node : meeting_nodes) {
                string p = "";
                pair<int, int> curr = meeting_node;
                while (parent[curr.first][curr.second].first != -2) {
                    p += move_char[curr.first][curr.second];
                    curr = parent[curr.first][curr.second];
                }
                reverse(p.begin(), p.end());
                if (check_and_print(p, ' ', false)) return 0;
            }
        }
    }

    cout << -1 << endl;

    return 0;
}