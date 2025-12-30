#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

int N, M;
vector<string> grid;
int sr, sc, er, ec;

// Directions: L, R, U, D
int dr[] = {0, 0, -1, 1};
int dc[] = {-1, 1, 0, 0};
char dchar[] = {'L', 'R', 'U', 'D'};

struct State {
    int r1, c1, r2, c2;
};

// Packed state for parent array to save space
struct ParentInfo {
    uint8_t pr1, pc1, pr2, pc2;
    uint8_t move_dir; // 0-3, 255 for start
};

ParentInfo parent[31][31][31][31];
int visited_bfs[31][31][31][31];
int search_id = 0;

// Reverse steps precomputed
// rev_step[r][c][dir] contains list of {prev_r, prev_c} such that step(prev, dir) -> (r,c)
vector<pair<int, int>> rev_step[31][31][4];

bool is_visited_cell[31][31];
int total_blanks = 0;
int visited_count = 0;

void get_next_pos(int r, int c, int k, int &nr, int &nc) {
    nr = r + dr[k];
    nc = c + dc[k];
    if (nr < 1 || nr > N || nc < 1 || nc > M || grid[nr-1][nc-1] == '0') {
        nr = r;
        nc = c;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    grid.resize(N);
    total_blanks = 0;
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
        for (char c : grid[i]) {
            if (c == '1') total_blanks++;
        }
    }
    cin >> sr >> sc >> er >> ec;

    // Precompute reverse steps
    for (int r = 1; r <= N; ++r) {
        for (int c = 1; c <= M; ++c) {
            if (grid[r-1][c-1] == '0') continue;
            for (int k = 0; k < 4; ++k) {
                int nr, nc;
                get_next_pos(r, c, k, nr, nc);
                rev_step[nr][nc][k].push_back({r, c});
            }
        }
    }

    // Mark start and end as visited
    is_visited_cell[sr][sc] = true;
    visited_count = 1;
    if (!is_visited_cell[er][ec]) {
        is_visited_cell[er][ec] = true;
        visited_count++;
    }

    State curr = {sr, sc, er, ec};
    string solution_prefix = "";

    // Greedy BFS phases
    while (visited_count < total_blanks) {
        search_id++;
        queue<State> q;
        q.push(curr);
        visited_bfs[curr.r1][curr.c1][curr.r2][curr.c2] = search_id;
        parent[curr.r1][curr.c1][curr.r2][curr.c2] = {0,0,0,0, 255};

        State target_state = {-1, -1, -1, -1};
        bool found = false;

        while (!q.empty()) {
            State u = q.front();
            q.pop();

            // Check if we visited a new blank cell
            if ((!is_visited_cell[u.r1][u.c1]) || (!is_visited_cell[u.r2][u.c2])) {
                target_state = u;
                found = true;
                break;
            }

            // Try all 4 moves
            for (int k = 0; k < 4; ++k) {
                int nr1, nc1;
                get_next_pos(u.r1, u.c1, k, nr1, nc1);
                
                // For v (the second component), we need v_prev such that step(v_prev, k) == u.r2, u.c2
                for (auto &prev : rev_step[u.r2][u.c2][k]) {
                    int nr2 = prev.first;
                    int nc2 = prev.second;
                    
                    if (visited_bfs[nr1][nc1][nr2][nc2] != search_id) {
                        visited_bfs[nr1][nc1][nr2][nc2] = search_id;
                        parent[nr1][nc1][nr2][nc2] = {(uint8_t)u.r1, (uint8_t)u.c1, (uint8_t)u.r2, (uint8_t)u.c2, (uint8_t)k};
                        q.push({nr1, nc1, nr2, nc2});
                    }
                }
            }
        }

        if (!found) {
            cout << -1 << endl;
            return 0;
        }

        // Reconstruct path segment and update visited
        string segment = "";
        State temp = target_state;
        while (true) {
            if (!is_visited_cell[temp.r1][temp.c1]) {
                is_visited_cell[temp.r1][temp.c1] = true;
                visited_count++;
            }
            if (!is_visited_cell[temp.r2][temp.c2]) {
                is_visited_cell[temp.r2][temp.c2] = true;
                visited_count++;
            }

            ParentInfo p = parent[temp.r1][temp.c1][temp.r2][temp.c2];
            if (p.move_dir == 255) break;
            segment += dchar[p.move_dir];
            temp = {(int)p.pr1, (int)p.pc1, (int)p.pr2, (int)p.pc2};
        }
        reverse(segment.begin(), segment.end());
        solution_prefix += segment;
        
        curr = target_state;
    }

    // Final phase: reach (k, k)
    search_id++;
    queue<State> q;
    q.push(curr);
    visited_bfs[curr.r1][curr.c1][curr.r2][curr.c2] = search_id;
    parent[curr.r1][curr.c1][curr.r2][curr.c2] = {0,0,0,0, 255};
    
    State final_state = {-1, -1, -1, -1};
    bool found = false;

    if (curr.r1 == curr.r2 && curr.c1 == curr.c2) {
        found = true;
        final_state = curr;
    } else {
        while (!q.empty()) {
            State u = q.front();
            q.pop();

            if (u.r1 == u.r2 && u.c1 == u.c2) {
                final_state = u;
                found = true;
                break;
            }

            for (int k = 0; k < 4; ++k) {
                int nr1, nc1;
                get_next_pos(u.r1, u.c1, k, nr1, nc1);
                for (auto &prev : rev_step[u.r2][u.c2][k]) {
                    int nr2 = prev.first;
                    int nc2 = prev.second;
                    if (visited_bfs[nr1][nc1][nr2][nc2] != search_id) {
                        visited_bfs[nr1][nc1][nr2][nc2] = search_id;
                        parent[nr1][nc1][nr2][nc2] = {(uint8_t)u.r1, (uint8_t)u.c1, (uint8_t)u.r2, (uint8_t)u.c2, (uint8_t)k};
                        q.push({nr1, nc1, nr2, nc2});
                    }
                }
            }
        }
    }

    if (!found) {
        cout << -1 << endl;
        return 0;
    }

    string final_segment = "";
    State temp = final_state;
    while (true) {
        ParentInfo p = parent[temp.r1][temp.c1][temp.r2][temp.c2];
        if (p.move_dir == 255) break;
        final_segment += dchar[p.move_dir];
        temp = {(int)p.pr1, (int)p.pc1, (int)p.pr2, (int)p.pc2};
    }
    reverse(final_segment.begin(), final_segment.end());
    solution_prefix += final_segment;

    string full_solution = solution_prefix;
    string reversed_sol = solution_prefix;
    reverse(reversed_sol.begin(), reversed_sol.end());
    full_solution += reversed_sol;

    cout << full_solution << endl;

    return 0;
}