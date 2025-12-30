#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <set>
#include <algorithm>

using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;
int total_blank_cells = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};
int opposite_move[] = {1, 0, 3, 2};

struct State {
    int r1, c1, r2, c2;
};

short dist[31][31][31][31];
State parent_state[31][31][31][31];
char parent_move[31][31][31][31];

bool is_valid(int r, int c) {
    return r >= 0 && r < n && c >= 0 && c < m && grid[r][c] == '1';
}

pair<int, int> get_next_pos(int r, int c, int move_idx) {
    int nr = r + dr[move_idx];
    int nc = c + dc[move_idx];
    if (is_valid(nr, nc)) {
        return {nr, nc};
    }
    return {r, c};
}

void check_and_print(State end_state, const string& center_move) {
    set<pair<int, int>> visited_cells;
    string path1 = "";
    
    State current_state = end_state;
    while (dist[current_state.r1][current_state.c1][current_state.r2][current_state.c2] > 0) {
        visited_cells.insert({current_state.r1, current_state.c1});
        visited_cells.insert({current_state.r2, current_state.c2});
        
        char move = parent_move[current_state.r1][current_state.c1][current_state.r2][current_state.c2];
        path1 += move;
        current_state = parent_state[current_state.r1][current_state.c1][current_state.r2][current_state.c2];
    }
    visited_cells.insert({sr, sc});
    visited_cells.insert({er, ec});

    if (visited_cells.size() == total_blank_cells) {
        reverse(path1.begin(), path1.end());
        string path2 = path1;
        reverse(path2.begin(), path2.end());
        cout << path1 << center_move << path2 << endl;
        exit(0);
    }
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

    if (total_blank_cells == 1) {
        if (sr == er && sc == ec) {
            cout << "" << endl;
        } else {
            cout << -1 << endl;
        }
        return 0;
    }
    
    vector<vector<bool>> visited_conn(n, vector<bool>(m, false));
    queue<pair<int, int>> q_conn;
    int reachable_blank = 0;

    q_conn.push({sr, sc});
    visited_conn[sr][sc] = true;
    reachable_blank++;

    while(!q_conn.empty()){
        pair<int, int> curr = q_conn.front();
        q_conn.pop();

        for(int i=0; i<4; ++i){
            int nr = curr.first + dr[i];
            int nc = curr.second + dc[i];
            if(is_valid(nr, nc) && !visited_conn[nr][nc]){
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


    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            for (int k = 0; k < n; ++k) {
                for (int l = 0; l < m; ++l) {
                    dist[i][j][k][l] = -1;
                }
            }
        }
    }

    queue<State> q;
    
    State start_state = {sr, sc, er, ec};
    q.push(start_state);
    dist[sr][sc][er][ec] = 0;
    
    while (!q.empty()) {
        State current = q.front();
        q.pop();
        
        // Even length palindrome
        if (current.r1 == current.r2 && current.c1 == current.c2) {
            check_and_print(current, "");
        }

        // Odd length palindrome
        for (int i = 0; i < 4; ++i) {
            pair<int, int> next_pos1 = get_next_pos(current.r1, current.c1, i);
            if (next_pos1.first == current.r2 && next_pos1.second == current.c2) {
                string center_move(1, move_chars[i]);
                check_and_print(current, center_move);
            }
        }
        
        if (dist[current.r1][current.c1][current.r2][current.c2] >= 2 * n * m) continue;

        for (int i = 0; i < 4; ++i) { // Move for person 1
            int move1_idx = i;
            int move2_idx = opposite_move[i];

            pair<int, int> next_pos1 = get_next_pos(current.r1, current.c1, move1_idx);
            pair<int, int> next_pos2 = get_next_pos(current.r2, current.c2, move2_idx);

            if (dist[next_pos1.first][next_pos1.second][next_pos2.first][next_pos2.second] == -1) {
                dist[next_pos1.first][next_pos1.second][next_pos2.first][next_pos2.second] = dist[current.r1][current.c1][current.r2][current.c2] + 1;
                parent_state[next_pos1.first][next_pos1.second][next_pos2.first][next_pos2.second] = current;
                parent_move[next_pos1.first][next_pos1.second][next_pos2.first][next_pos2.second] = move_chars[move1_idx];
                q.push({next_pos1.first, next_pos1.second, next_pos2.first, next_pos2.second});
            }
        }
    }

    cout << -1 << endl;

    return 0;
}