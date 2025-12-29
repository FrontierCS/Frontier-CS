#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <utility>
#include <algorithm>
#include <set>

using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;
int total_blank_cells = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char moves[] = {'U', 'D', 'L', 'R'};

struct State {
    int r1, c1, r2, c2;
};

pair<int, int> do_move(int r, int c, char move_char) {
    int move_idx = -1;
    if (move_char == 'U') move_idx = 0;
    else if (move_char == 'D') move_idx = 1;
    else if (move_char == 'L') move_idx = 2;
    else if (move_char == 'R') move_idx = 3;

    int nr = r + dr[move_idx];
    int nc = c + dc[move_idx];

    if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
        return {nr, nc};
    }
    return {r, c};
}

vector<pair<int, int>> rev_move[30][30][4];
int dist[30][30][30][30];
State parent_state[30][30][30][30];
char parent_move[30][30][30][30];

void precompute_rev_moves() {
    for (int r = 0; r < n; ++r) {
        for (int c = 0; c < m; ++c) {
            if (grid[r][c] == '0') continue;
            for (int i = 0; i < 4; ++i) {
                pair<int, int> next_pos = do_move(r, c, moves[i]);
                rev_move[next_pos.first][next_pos.second][i].push_back({r, c});
            }
        }
    }
}

string get_solution_path(int ur, int uc, int vr, int vc, char mid_move) {
    string half_path = "";
    int cur_ur = ur, cur_uc = uc, cur_vr = vr, cur_vc = vc;
    while (cur_ur != sr || cur_uc != sc || cur_vr != er || cur_vc != ec) {
        char move = parent_move[cur_ur][cur_uc][cur_vr][cur_vc];
        half_path += move;
        State p = parent_state[cur_ur][cur_uc][cur_vr][cur_vc];
        cur_ur = p.r1;
        cur_uc = p.c1;
        cur_vr = p.r2;
        cur_vc = p.c2;
    }
    reverse(half_path.begin(), half_path.end());
    
    string second_half = half_path;
    reverse(second_half.begin(), second_half.end());
    
    if (mid_move != ' ') {
        return half_path + mid_move + second_half;
    }
    return half_path + second_half;
}

bool check_solution(const string& s) {
    if (total_blank_cells == 0) return true;
    set<pair<int, int>> visited_cells;
    int r = sr, c = sc;
    visited_cells.insert({r, c});

    for (char move : s) {
        pair<int, int> next_pos = do_move(r, c, move);
        r = next_pos.first;
        c = next_pos.second;
        visited_cells.insert({r, c});
    }
    
    if (r != er || c != ec) {
        return false;
    }
    return visited_cells.size() == total_blank_cells;
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
            if (check_solution("")) {
                cout << "" << endl;
            } else {
                cout << -1 << endl;
            }
        } else {
            cout << -1 << endl;
        }
        return 0;
    }
    
    if (sr == er && sc == ec) {
        if(check_solution("")) {
            cout << "" << endl;
            return 0;
        }
    }

    precompute_rev_moves();
    
    for (int i=0; i<n; ++i) for (int j=0; j<m; ++j) for (int k=0; k<n; ++k) for(int l=0; l<m; ++l) dist[i][j][k][l] = -1;

    queue<State> q;
    q.push({sr, sc, er, ec});
    dist[sr][sc][er][ec] = 0;

    int current_dist = -1;
    vector<string> solutions;

    while (!q.empty()) {
        State curr = q.front();
        q.pop();
        int d = dist[curr.r1][curr.c1][curr.r2][curr.c2];

        if (d > current_dist) {
            if (!solutions.empty()) {
                string best_sol = solutions[0];
                for (size_t i = 1; i < solutions.size(); ++i) {
                    if (solutions[i].length() < best_sol.length()) {
                        best_sol = solutions[i];
                    }
                }
                cout << best_sol << endl;
                return 0;
            }
            current_dist = d;
        }

        // Even length solution: 2*d
        if (curr.r1 == curr.r2 && curr.c1 == curr.c2) {
            string sol = get_solution_path(curr.r1, curr.c1, curr.r2, curr.c2, ' ');
            if (check_solution(sol)) {
                solutions.push_back(sol);
            }
        }

        // Odd length solution: 2*d + 1
        for (int i = 0; i < 4; ++i) {
            pair<int, int> next_u = do_move(curr.r1, curr.c1, moves[i]);
            if (next_u.first == curr.r2 && next_u.second == curr.c2) {
                string sol = get_solution_path(curr.r1, curr.c1, curr.r2, curr.c2, moves[i]);
                if (check_solution(sol)) {
                    // This is a candidate for len 2d+1, will be checked after all len 2d
                }
            }
        }
        
        for (int i = 0; i < 4; ++i) {
            pair<int, int> next_u = do_move(curr.r1, curr.c1, moves[i]);
            for (const auto& prev_v : rev_move[curr.r2][curr.c2][i]) {
                if (dist[next_u.first][next_u.second][prev_v.first][prev_v.second] == -1) {
                    dist[next_u.first][next_u.second][prev_v.first][prev_v.second] = d + 1;
                    parent_state[next_u.first][next_u.second][prev_v.first][prev_v.second] = curr;
                    parent_move[next_u.first][next_u.second][prev_v.first][prev_v.second] = moves[i];
                    q.push({next_u.first, next_u.second, prev_v.first, prev_v.second});
                }
            }
        }
    }
    
    // Process odd-length solutions from the last fully processed level.
    current_dist++;
    vector<string> odd_solutions;
    for(int r1=0; r1<n; ++r1) for(int c1=0; c1<m; ++c1) for(int r2=0; r2<n; ++r2) for(int c2=0; c2<m; ++c2) {
        if(dist[r1][c1][r2][c2] == current_dist -1) {
             for (int i = 0; i < 4; ++i) {
                pair<int, int> next_u = do_move(r1, c1, moves[i]);
                if (next_u.first == r2 && next_u.second == c2) {
                    string sol = get_solution_path(r1,c1,r2,c2, moves[i]);
                    if (check_solution(sol)) {
                        odd_solutions.push_back(sol);
                    }
                }
            }
        }
    }

    if (!solutions.empty()) {
        string best_sol = solutions[0];
        for (size_t i = 1; i < solutions.size(); ++i) {
            if (solutions[i].length() < best_sol.length()) best_sol = solutions[i];
        }
        if(!odd_solutions.empty()){
            string best_odd = odd_solutions[0];
            for (size_t i = 1; i < odd_solutions.size(); ++i) {
                if (odd_solutions[i].length() < best_odd.length()) best_odd = odd_solutions[i];
            }
            if (best_odd.length() < best_sol.length()) best_sol = best_odd;
        }
        cout << best_sol << endl;
    } else if (!odd_solutions.empty()){
        string best_odd = odd_solutions[0];
        for (size_t i = 1; i < odd_solutions.size(); ++i) {
            if (odd_solutions[i].length() < best_odd.length()) best_odd = odd_solutions[i];
        }
        cout << best_odd << endl;
    } else {
        cout << -1 << endl;
    }

    return 0;
}