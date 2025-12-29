#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <set>

using namespace std;

int n, m;
vector<string> grid;
int sr, sc, er, ec;

int total_blank_cells = 0;

pair<int, int> do_move(int r, int c, char move_char) {
    int dr = 0, dc = 0;
    if (move_char == 'U') dr = -1;
    else if (move_char == 'D') dr = 1;
    else if (move_char == 'L') dc = -1;
    else if (move_char == 'R') dc = 1;

    int nr = r + dr;
    int nc = c + dc;

    if (nr >= 0 && nr < n && nc >= 0 && nc < m && grid[nr][nc] == '1') {
        return {nr, nc};
    }
    return {r, c};
}

char moves[] = {'U', 'D', 'L', 'R'};

struct State {
    int r1, c1, r2, c2;
};

int dist[30][30][30][30];
State parent[30][30][30][30];
char move_to[30][30][30][30];

bool verify(const string& s) {
    if (total_blank_cells == 0) return true;

    set<pair<int, int>> visited;
    int r = sr, c = sc;
    visited.insert({r, c});

    for (char move_char : s) {
        pair<int, int> next_pos = do_move(r, c, move_char);
        r = next_pos.first;
        c = next_pos.second;
        visited.insert({r, c});
    }

    if (r != er || c != ec) return false;
    return visited.size() == total_blank_cells;
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
    
    if (total_blank_cells > 0) {
        queue<pair<int, int>> q_check;
        q_check.push({sr, sc});
        set<pair<int, int>> visited_check;
        visited_check.insert({sr, sc});
        while(!q_check.empty()){
            auto curr = q_check.front();
            q_check.pop();
            for(char mv : moves){
                auto next = do_move(curr.first, curr.second, mv);
                if(visited_check.find(next) == visited_check.end() && grid[next.first][next.second]=='1'){
                    visited_check.insert(next);
                    q_check.push(next);
                }
            }
        }
        if(visited_check.size() != total_blank_cells){
            cout << -1 << endl;
            return 0;
        }
    }

    for (int i = 0; i < n; ++i) for (int j = 0; j < m; ++j)
    for (int k = 0; k < n; ++k) for (int l = 0; l < m; ++l)
        dist[i][j][k][l] = -1;

    queue<State> q;
    dist[sr][sc][er][ec] = 0;
    q.push({sr, sc, er, ec});
    
    while (!q.empty()) {
        int level_size = q.size();
        string best_solution = "";
        vector<State> current_level_nodes;
        for(int i=0; i<level_size; ++i){
            current_level_nodes.push_back(q.front());
            q.pop();
        }

        for (const auto& curr : current_level_nodes) {
            string prefix = "";
            State temp = curr;
            while (dist[temp.r1][temp.c1][temp.r2][temp.c2] > 0) {
                char m = move_to[temp.r1][temp.c1][temp.r2][temp.c2];
                prefix += m;
                temp = parent[temp.r1][temp.c1][temp.r2][temp.c2];
            }
            reverse(prefix.begin(), prefix.end());
            
            string rev_prefix = prefix;
            reverse(rev_prefix.begin(), rev_prefix.end());
            
            // Case 1: Even length palindrome
            if (curr.r1 == curr.r2 && curr.c1 == curr.c2) {
                string full_path = prefix + rev_prefix;
                if (verify(full_path)) {
                    if (best_solution == "" || full_path.length() < best_solution.length()) {
                        best_solution = full_path;
                    }
                }
            }
            
            // Case 2: Odd length palindrome
            for (char mid_move : moves) {
                pair<int, int> next_pos = do_move(curr.r1, curr.c1, mid_move);
                if (next_pos.first == curr.r2 && next_pos.second == curr.c2) {
                    string full_path = prefix + mid_move + rev_prefix;
                    if (verify(full_path)) {
                        if (best_solution == "" || full_path.length() < best_solution.length()) {
                            best_solution = full_path;
                        }
                    }
                }
            }
        }
        
        if (best_solution != "") {
            cout << best_solution << endl;
            return 0;
        }
        
        // expand for next level
        for (const auto& curr : current_level_nodes) {
            for (char m : moves) {
                pair<int, int> next1 = do_move(curr.r1, curr.c1, m);
                pair<int, int> next2 = do_move(curr.r2, curr.c2, m);
                
                if (dist[next1.first][next1.second][next2.first][next2.second] == -1) {
                    dist[next1.first][next1.second][next2.first][next2.second] = dist[curr.r1][curr.c1][curr.r2][curr.c2] + 1;
                    parent[next1.first][next1.second][next2.first][next2.second] = curr;
                    move_to[next1.first][next1.second][next2.first][next2.second] = m;
                    q.push({next1.first, next1.second, next2.first, next2.second});
                }
            }
        }
    }
    
    cout << -1 << endl;

    return 0;
}