#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <algorithm>

using namespace std;

const string templ[] = {
    "0   0   000 ",
    "00 00  0   0",
    "0 0 0  0   0",
    "0 0 0  0000 ",
    "0 0 0  0    ",
    "0   0  0    ",
    "            ",
    "0  0   00000",
    "0 0      0  ",
    "00   0 0 0  ",
    "0 0  0 0 0  ",
    "0  0 000 0  "
};

int grid_state[14][14];
int clues[12][12];
int target_task = 0;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

struct Point { int r, c; };

bool check_zeros() {
    bool visited[14][14];
    memset(visited, 0, sizeof(visited));
    vector<Point> q;
    q.push_back({0, 0});
    visited[0][0] = true;
    int head = 0;
    int count = 0;
    int total_zeros = 0;
    for(int i=0; i<14; i++)
        for(int j=0; j<14; j++)
            if(grid_state[i][j] == 0) total_zeros++;

    while(head < q.size()){
        Point p = q[head++];
        count++;
        for(int i=0; i<4; i++){
            int nr = p.r + dr[i];
            int nc = p.c + dc[i];
            if(nr>=0 && nr<14 && nc>=0 && nc<14 && !visited[nr][nc] && grid_state[nr][nc] == 0){
                visited[nr][nc] = true;
                q.push_back({nr, nc});
            }
        }
    }
    return count == total_zeros;
}

bool check_checkerboard() {
    for(int i=0; i<13; i++){
        for(int j=0; j<13; j++){
            int s = grid_state[i][j] + grid_state[i+1][j] + grid_state[i][j+1] + grid_state[i+1][j+1];
            if(s == 2) {
                if(grid_state[i][j] == grid_state[i+1][j+1]) return false;
            }
        }
    }
    return true;
}

bool compute_and_check_clues() {
    for(int i=0; i<12; i++){
        for(int j=0; j<12; j++){
            if(templ[i][j] != ' ') {
                int r = i + 1;
                int c = j + 1;
                int v = 0;
                if(grid_state[r-1][c] != grid_state[r][c]) v++;
                if(grid_state[r+1][c] != grid_state[r][c]) v++;
                if(grid_state[r][c-1] != grid_state[r][c]) v++;
                if(grid_state[r][c+1] != grid_state[r][c]) v++;
                clues[i][j] = v;
                if(target_task == 1 && v == 0) return false;
                if(v == 4) return false;
            } else {
                clues[i][j] = -1;
            }
        }
    }
    return true;
}

int solution_count = 0;
int solve_grid[14][14];
int fixed_clues[12][12];
int parent[196];

int find_set(int v) { return v == parent[v] ? v : parent[v] = find_set(parent[v]); }
void union_sets(int a, int b) { a = find_set(a); b = find_set(b); if(a!=b) parent[b] = a; }

void solve(int idx) {
    if(solution_count > 1) return;
    if(idx == 144) {
        int ones = 0;
        for(int i=0; i<196; i++) parent[i] = i;
        for(int r=1; r<=12; r++){
            for(int c=1; c<=12; c++){
                if(solve_grid[r][c] == 1){
                    ones++;
                    if(solve_grid[r-1][c] == 1) union_sets(r*14+c, (r-1)*14+c);
                    if(solve_grid[r][c-1] == 1) union_sets(r*14+c, r*14+(c-1));
                }
            }
        }
        if(ones == 0) return;
        int roots = 0;
        for(int r=1; r<=12; r++){
            for(int c=1; c<=12; c++){
                if(solve_grid[r][c] == 1 && parent[r*14+c] == r*14+c) roots++;
            }
        }
        if(roots != 1) return;

        for(int i=0; i<196; i++) parent[i] = i;
        for(int i=0; i<14; i++){
            union_sets(0, i); union_sets(0, 13*14+i);
            union_sets(0, i*14); union_sets(0, i*14+13);
        }
        for(int r=1; r<=12; r++){
            for(int c=1; c<=12; c++){
                if(solve_grid[r][c] == 0){
                    if(solve_grid[r-1][c] == 0) union_sets(r*14+c, (r-1)*14+c);
                    if(solve_grid[r][c-1] == 0) union_sets(r*14+c, r*14+(c-1));
                    if(solve_grid[r+1][c] == 0) union_sets(r*14+c, (r+1)*14+c);
                    if(solve_grid[r][c+1] == 0) union_sets(r*14+c, r*14+(c+1));
                }
            }
        }
        for(int r=1; r<=12; r++){
            for(int c=1; c<=12; c++){
                if(solve_grid[r][c] == 0){
                    if(find_set(r*14+c) != find_set(0)) return;
                }
            }
        }
        solution_count++;
        return;
    }

    int r = idx / 12 + 1;
    int c = idx % 12 + 1;

    for(int val=0; val<=1; val++){
        solve_grid[r][c] = val;
        
        if(r > 1 && c > 1) {
            int s = solve_grid[r-1][c-1] + solve_grid[r-1][c] + solve_grid[r][c-1] + solve_grid[r][c];
            if(s == 2 && solve_grid[r-1][c-1] == solve_grid[r][c]) continue; 
        }

        if(r > 1) {
            int cr = r-1; int cc = c;
            int clue = fixed_clues[cr-1][cc-1];
            if(clue != -1) {
                int diff = 0;
                diff += (solve_grid[cr-1][cc] != solve_grid[cr][cc]);
                diff += (solve_grid[cr+1][cc] != solve_grid[cr][cc]);
                diff += (solve_grid[cr][cc-1] != solve_grid[cr][cc]);
                diff += (solve_grid[cr][cc+1] != solve_grid[cr][cc]);
                if(diff != clue) continue;
            }
        }
        
        if(r == 12 && c > 1) {
            int cr = r; int cc = c-1;
            int clue = fixed_clues[cr-1][cc-1];
            if(clue != -1) {
                int diff = 0;
                diff += (solve_grid[cr-1][cc] != solve_grid[cr][cc]);
                diff += (solve_grid[cr+1][cc] != solve_grid[cr][cc]);
                diff += (solve_grid[cr][cc-1] != solve_grid[cr][cc]);
                diff += (solve_grid[cr][cc+1] != solve_grid[cr][cc]);
                if(diff != clue) continue;
            }
        }
        if(r == 12 && c == 12) {
             int cr = r; int cc = c;
             int clue = fixed_clues[cr-1][cc-1];
             if(clue != -1) {
                 int diff = 0;
                 diff += (solve_grid[cr-1][cc] != solve_grid[cr][cc]);
                 diff += (solve_grid[cr+1][cc] != solve_grid[cr][cc]);
                 diff += (solve_grid[cr][cc-1] != solve_grid[cr][cc]);
                 diff += (solve_grid[cr][cc+1] != solve_grid[cr][cc]);
                 if(diff != clue) continue;
             }
        }
        
        solve(idx + 1);
        if(solution_count > 1) return;
    }
}

int main() {
    if(cin >> target_task){} else target_task=0;
    srand(target_task == 0 ? 123 : 9999); 
    
    while(true) {
        memset(grid_state, 0, sizeof(grid_state));
        int start_r = 4 + rand() % 4;
        int start_c = 4 + rand() % 4;
        grid_state[start_r][start_c] = 1;
        
        int steps = 50 + rand() % 50;
        for(int k=0; k<steps; k++){
            vector<Point> cands;
            for(int r=1; r<=12; r++){
                for(int c=1; c<=12; c++){
                    if(grid_state[r][c] == 0) {
                        bool adj = false;
                        if(grid_state[r-1][c]) adj=true;
                        else if(grid_state[r+1][c]) adj=true;
                        else if(grid_state[r][c-1]) adj=true;
                        else if(grid_state[r][c+1]) adj=true;
                        if(adj) cands.push_back({r, c});
                    }
                }
            }
            if(cands.empty()) break;
            random_shuffle(cands.begin(), cands.end());
            bool moved = false;
            for(size_t i=0; i<cands.size(); i++) {
                Point p = cands[i];
                grid_state[p.r][p.c] = 1;
                if(check_checkerboard() && check_zeros()) {
                    moved = true;
                    break;
                }
                grid_state[p.r][p.c] = 0;
            }
            if(!moved) break;
        }
        
        if(!compute_and_check_clues()) continue;
        
        memset(solve_grid, 0, sizeof(solve_grid));
        memcpy(fixed_clues, clues, sizeof(clues));
        solution_count = 0;
        solve(0);
        
        if(solution_count == 1) {
            for(int i=0; i<12; i++){
                for(int j=0; j<12; j++){
                    if(templ[i][j] != ' ')
                        cout << clues[i][j];
                    else
                        cout << " ";
                }
                cout << endl;
            }
            break;
        }
    }
    return 0;
}