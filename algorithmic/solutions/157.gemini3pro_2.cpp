#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <cmath>
#include <random>
#include <queue>
#include <chrono>
#include <set>
#include <cassert>

using namespace std;

// Constants and Types
const int UP = 2;
const int DOWN = 8;
const int LEFT = 1;
const int RIGHT = 4;
const int DR[4] = {-1, 1, 0, 0};
const int DC[4] = {0, 0, -1, 1};
const char DIR_CHAR[4] = {'U', 'D', 'L', 'R'};

struct Point {
    int r, c;
    bool operator==(const Point& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Point& other) const { return r != other.r || c != other.c; }
    bool operator<(const Point& other) const { return r < other.r || (r == other.r && c < other.c); }
};

int N, T;
vector<vector<int>> initial_board;
int empty_tile_id; 

int get_pattern(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'a' + 10;
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Evaluate board for SA
pair<int, int> evaluate(const vector<vector<int>>& board) {
    int mismatches = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int p = board[r][c];
            if (p == 0) continue; 
            
            // Check Right
            if (c + 1 < N) {
                int p_right = board[r][c+1];
                bool l_right = (p & RIGHT);
                bool r_left = (p_right & LEFT);
                if (l_right != r_left) mismatches++;
            } else {
                if (p & RIGHT) mismatches++;
            }
            
            // Check Down
            if (r + 1 < N) {
                int p_down = board[r+1][c];
                bool l_down = (p & DOWN);
                bool d_up = (p_down & UP);
                if (l_down != d_up) mismatches++;
            } else {
                if (p & DOWN) mismatches++;
            }
            
            // Boundary checks
            if (c == 0 && (p & LEFT)) mismatches++;
            if (r == 0 && (p & UP)) mismatches++;
        }
    }

    int max_comp = 0;
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (board[r][c] == 0) continue;
            if (visited[r][c]) continue;
            
            int comp_size = 0;
            queue<Point> q;
            q.push({r, c});
            visited[r][c] = true;
            while (!q.empty()) {
                Point u = q.front(); q.pop();
                comp_size++;
                int p = board[u.r][u.c];
                
                if ((p & UP) && u.r > 0) {
                     if ((board[u.r-1][u.c] & DOWN) && !visited[u.r-1][u.c]) {
                         visited[u.r-1][u.c] = true;
                         q.push({u.r-1, u.c});
                     }
                }
                if ((p & DOWN) && u.r < N - 1) {
                     if ((board[u.r+1][u.c] & UP) && !visited[u.r+1][u.c]) {
                         visited[u.r+1][u.c] = true;
                         q.push({u.r+1, u.c});
                     }
                }
                if ((p & LEFT) && u.c > 0) {
                     if ((board[u.r][u.c-1] & RIGHT) && !visited[u.r][u.c-1]) {
                         visited[u.r][u.c-1] = true;
                         q.push({u.r, u.c-1});
                     }
                }
                if ((p & RIGHT) && u.c < N - 1) {
                     if ((board[u.r][u.c+1] & LEFT) && !visited[u.r][u.c+1]) {
                         visited[u.r][u.c+1] = true;
                         q.push({u.r, u.c+1});
                     }
                }
            }
            if (comp_size > max_comp) max_comp = comp_size;
        }
    }
    
    int score = max_comp * 100 - mismatches * 1000;
    if (mismatches == 0 && max_comp == N*N - 1) score += 100000;
    
    return {score, max_comp};
}

struct PuzzleSolver {
    int N;
    vector<vector<int>> current_ids;
    Point empty_pos;
    vector<int> tile_type_of_id;
    vector<Point> target_pos_of_id;
    string moves;

    PuzzleSolver(int n, vector<vector<int>> ids, Point ep, vector<int> types) 
        : N(n), current_ids(ids), empty_pos(ep), tile_type_of_id(types) {}

    void move_empty(int dir) { 
        int nr = empty_pos.r + DR[dir];
        int nc = empty_pos.c + DC[dir];
        if (nr < 0 || nr >= N || nc < 0 || nc >= N) return;
        swap(current_ids[empty_pos.r][empty_pos.c], current_ids[nr][nc]);
        empty_pos = {nr, nc};
        moves += DIR_CHAR[dir];
    }

    bool path_empty_to(Point target, const vector<vector<bool>>& fixed) {
        if (empty_pos == target) return true;
        
        queue<Point> q;
        q.push(empty_pos);
        
        vector<vector<int>> dist(N, vector<int>(N, -1));
        dist[empty_pos.r][empty_pos.c] = 0;
        vector<vector<int>> from_dir(N, vector<int>(N, -1));

        while(!q.empty()){
            Point u = q.front(); q.pop();
            if (u == target) break;
            
            for(int k=0; k<4; ++k){
                int nr = u.r + DR[k];
                int nc = u.c + DC[k];
                if(nr>=0 && nr<N && nc>=0 && nc<N && !fixed[nr][nc] && dist[nr][nc] == -1){
                    dist[nr][nc] = dist[u.r][u.c] + 1;
                    from_dir[nr][nc] = k;
                    q.push({nr, nc});
                }
            }
        }

        if (dist[target.r][target.c] == -1) return false;

        string path = "";
        Point cur = target;
        while(cur != empty_pos){
            int dir = from_dir[cur.r][cur.c];
            path += DIR_CHAR[dir];
            cur.r -= DR[dir];
            cur.c -= DC[dir];
        }
        reverse(path.begin(), path.end());
        
        for(char c : path){
            if(c == 'U') move_empty(0);
            else if(c == 'D') move_empty(1);
            else if(c == 'L') move_empty(2);
            else if(c == 'R') move_empty(3);
        }
        return true;
    }

    void move_tile(int id, Point dest, vector<vector<bool>>& fixed) {
        Point cur = {-1, -1};
        for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) if(current_ids[r][c] == id) cur = {r, c};
        
        while(cur != dest) {
            int dr = 0, dc = 0;
            if (cur.c < dest.c) dc = 1;
            else if (cur.c > dest.c) dc = -1;
            else if (cur.r < dest.r) dr = 1;
            else if (cur.r > dest.r) dr = -1;
            
            Point next = {cur.r + dr, cur.c + dc};
            
            fixed[cur.r][cur.c] = true;
            bool ok = path_empty_to(next, fixed);
            fixed[cur.r][cur.c] = false;
            
            if(!ok) {
                if (dc != 0 && cur.r != dest.r) {
                    dr = (cur.r < dest.r) ? 1 : -1;
                    dc = 0;
                    next = {cur.r + dr, cur.c + dc};
                    fixed[cur.r][cur.c] = true;
                    ok = path_empty_to(next, fixed);
                    fixed[cur.r][cur.c] = false;
                }
            }
            if (!ok) return; 
            
            int move_dir = -1;
            for(int k=0; k<4; ++k) if(next.r + DR[k] == cur.r && next.c + DC[k] == cur.c) move_dir = k;
            move_empty(move_dir);
            cur = next;
        }
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> T)) return 0;

    initial_board.resize(N, vector<int>(N));
    vector<int> tile_counts(16, 0);
    vector<vector<int>> initial_ids(N, vector<int>(N));
    vector<int> tile_type_of_id(N*N);
    Point initial_empty;

    for (int r = 0; r < N; ++r) {
        string s; cin >> s;
        for (int c = 0; c < N; ++c) {
            int p = get_pattern(s[c]);
            initial_board[r][c] = p;
            tile_counts[p]++;
            initial_ids[r][c] = r*N + c;
            tile_type_of_id[r*N + c] = p;
            if (p == 0) {
                initial_empty = {r, c};
                empty_tile_id = r*N + c;
            }
        }
    }

    vector<vector<int>> target_board(N, vector<int>(N));
    vector<int> available_tiles;
    for(int p=1; p<16; ++p) {
        for(int k=0; k<tile_counts[p]; ++k) available_tiles.push_back(p);
    }
    shuffle(available_tiles.begin(), available_tiles.end(), rng);
    
    int idx = 0;
    for(int r=0; r<N; ++r){
        for(int c=0; c<N; ++c){
            if(r == N-1 && c == N-1) target_board[r][c] = 0;
            else target_board[r][c] = available_tiles[idx++];
        }
    }

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.0; 
    
    auto current_score = evaluate(target_board);
    int best_score_val = current_score.first;
    vector<vector<int>> best_board = target_board;
    double temp = 1000.0;
    double cool = 0.9999;
    int iter = 0;

    while(true) {
        iter++;
        if ((iter & 255) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration<double>(now - start_time).count() > time_limit) break;
        }
        int r1 = rng() % N, c1 = rng() % N;
        if (r1 == N-1 && c1 == N-1) continue;
        int r2 = rng() % N, c2 = rng() % N;
        if (r2 == N-1 && c2 == N-1) continue;
        if (r1 == r2 && c1 == c2) continue;
        if (target_board[r1][c1] == target_board[r2][c2]) continue;

        swap(target_board[r1][c1], target_board[r2][c2]);
        auto new_score = evaluate(target_board);

        int delta = new_score.first - current_score.first;
        if (delta >= 0 || exp(delta / temp) > (double)(rng()%10000)/10000.0) {
            current_score = new_score;
            if (current_score.first > best_score_val) {
                best_score_val = current_score.first;
                best_board = target_board;
                if (best_score_val > 90000) break;
            }
        } else {
            swap(target_board[r1][c1], target_board[r2][c2]);
        }
        temp *= cool;
    }
    target_board = best_board;

    vector<Point> target_pos_of_id(N*N);
    vector<vector<Point>> type_targets(16);
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) type_targets[target_board[r][c]].push_back({r, c});
    
    vector<vector<int>> type_sources(16);
    for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) type_sources[initial_board[r][c]].push_back(initial_ids[r][c]);

    for(int t=0; t<16; ++t) {
        if (t == 0) {
            target_pos_of_id[type_sources[0][0]] = type_targets[0][0];
            continue;
        }
        vector<bool> used_target(type_targets[t].size(), false);
        for(int id : type_sources[t]) {
            int r_curr = id / N;
            int c_curr = id % N;
            int best_idx = -1;
            int min_dist = 1e9;
            for(int i=0; i<(int)type_targets[t].size(); ++i) {
                if (used_target[i]) continue;
                int d = abs(r_curr - type_targets[t][i].r) + abs(c_curr - type_targets[t][i].c);
                if (d < min_dist) {
                    min_dist = d;
                    best_idx = i;
                }
            }
            used_target[best_idx] = true;
            target_pos_of_id[id] = type_targets[t][best_idx];
        }
    }

    vector<vector<int>> target_id_grid(N, vector<int>(N));
    for(int id=0; id<N*N; ++id) {
        Point p = target_pos_of_id[id];
        target_id_grid[p.r][p.c] = id;
    }
    
    auto count_inversions = [&](const vector<vector<int>>& board) {
        vector<int> flat;
        for(int r=0; r<N; ++r) for(int c=0; c<N; ++c) {
            if (tile_type_of_id[board[r][c]] != 0) flat.push_back(board[r][c]);
        }
        int inv = 0;
        for(size_t i=0; i<flat.size(); ++i) for(size_t j=i+1; j<flat.size(); ++j) if (flat[i] > flat[j]) inv++;
        return inv;
    };
    
    int inv_curr = count_inversions(initial_ids);
    int inv_target = count_inversions(target_id_grid);
    int dist_empty = abs(initial_empty.r - (N-1)) + abs(initial_empty.c - (N-1));
    
    if ((inv_curr + inv_target + dist_empty) % 2 != 0) {
        for(int t=1; t<16; ++t) {
            if (tile_counts[t] >= 2) {
                int id1 = -1, id2 = -1;
                for(int id=0; id<N*N; ++id) {
                    if (tile_type_of_id[id] == t) {
                        if (id1 == -1) id1 = id;
                        else { id2 = id; break; }
                    }
                }
                Point p1 = target_pos_of_id[id1];
                Point p2 = target_pos_of_id[id2];
                target_pos_of_id[id1] = p2;
                target_pos_of_id[id2] = p1;
                target_id_grid[p1.r][p1.c] = id2;
                target_id_grid[p2.r][p2.c] = id1;
                break;
            }
        }
    }

    PuzzleSolver solver(N, initial_ids, initial_empty, tile_type_of_id);
    solver.target_pos_of_id = target_pos_of_id;
    vector<vector<bool>> fixed(N, vector<bool>(N, false));

    for(int r=0; r<=N-3; ++r) {
        for(int c=0; c<=N-3; ++c) {
            int target_id = target_id_grid[r][c];
            solver.move_tile(target_id, {r, c}, fixed);
            fixed[r][c] = true;
        }
        int id1 = target_id_grid[r][N-2];
        int id2 = target_id_grid[r][N-1];
        solver.move_tile(id1, {r, N-2}, fixed);
        
        int r2 = -1, c2 = -1;
        for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) if(solver.current_ids[i][j] == id2) {r2=i; c2=j;}
        
        if (r2 == r && c2 == N-1) {
            fixed[r][N-2] = true;
            fixed[r][N-1] = true;
        } else {
            solver.move_tile(id2, {r, N-2}, fixed);
            fixed[r][N-2] = true; 
            solver.move_tile(id1, {r+1, N-2}, fixed);
            fixed[r+1][N-2] = true; 
            solver.path_empty_to({r, N-1}, fixed);
            fixed[r][N-2] = false;
            fixed[r+1][N-2] = false;
            solver.move_empty(2); 
            solver.move_empty(1); 
            fixed[r][N-2] = true;
            fixed[r][N-1] = true;
        }
    }

    for(int c=0; c<=N-3; ++c) {
        int id1 = target_id_grid[N-2][c];
        int id2 = target_id_grid[N-1][c];
        solver.move_tile(id2, {N-2, c}, fixed);
        fixed[N-2][c] = true;
        solver.move_tile(id1, {N-2, c+1}, fixed);
        fixed[N-2][c+1] = true;
        solver.path_empty_to({N-1, c}, fixed);
        fixed[N-2][c] = false;
        fixed[N-2][c+1] = false;
        solver.move_empty(0);
        solver.move_empty(3);
        fixed[N-2][c] = true;
        fixed[N-1][c] = true;
    }

    auto get_2x2_state = [&]() {
        vector<int> s;
        s.push_back(solver.current_ids[N-2][N-2]);
        s.push_back(solver.current_ids[N-2][N-1]);
        s.push_back(solver.current_ids[N-1][N-2]);
        s.push_back(solver.current_ids[N-1][N-1]);
        return s;
    };
    
    vector<int> target_2x2;
    target_2x2.push_back(target_id_grid[N-2][N-2]);
    target_2x2.push_back(target_id_grid[N-2][N-1]);
    target_2x2.push_back(target_id_grid[N-1][N-2]);
    target_2x2.push_back(target_id_grid[N-1][N-1]);
    
    map<vector<int>, string> dist_map;
    queue<pair<vector<int>, string>> q;
    vector<int> start_state = get_2x2_state();
    dist_map[start_state] = "";
    q.push({start_state, ""});
    string sol_path = "";
    
    while(!q.empty()){
        auto [u, path] = q.front(); q.pop();
        if (u == target_2x2) {
            sol_path = path;
            break;
        }
        if (path.length() > 22) continue;
        int z = -1;
        for(int i=0; i<4; ++i) if(u[i] == empty_tile_id) z=i;
        int r = z / 2, c = z % 2;
        for(int k=0; k<4; ++k) {
            int nr = r + DR[k];
            int nc = c + DC[k];
            if (nr >= 0 && nr < 2 && nc >= 0 && nc < 2) {
                int nz = nr * 2 + nc;
                vector<int> v = u;
                swap(v[z], v[nz]);
                if (dist_map.find(v) == dist_map.end()) {
                    dist_map[v] = path + DIR_CHAR[k];
                    q.push({v, path + DIR_CHAR[k]});
                }
            }
        }
    }
    
    for(char c : sol_path) {
        if(c == 'U') solver.move_empty(0);
        else if(c == 'D') solver.move_empty(1);
        else if(c == 'L') solver.move_empty(2);
        else if(c == 'R') solver.move_empty(3);
    }

    cout << solver.moves << endl;
    return 0;
}