#include <bits/stdc++.h>
using namespace std;

const int UP = 2;
const int DOWN = 8;
const int LEFT = 1;
const int RIGHT = 4;

int N, T;
vector<vector<int>> board;
int empty_r, empty_c;

int hex_to_int(char c) {
    if ('0' <= c && c <= '9') return c - '0';
    return c - 'a' + 10;
}

// compute size of largest connected component
int compute_S(const vector<vector<int>>& b) {
    int n = b.size();
    vector<vector<bool>> visited(n, vector<bool>(n, false));
    int max_comp = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (b[i][j] == 0 || visited[i][j]) continue;
            // BFS
            queue<pair<int,int>> q;
            q.push({i, j});
            visited[i][j] = true;
            int sz = 0;
            while (!q.empty()) {
                auto [r, c] = q.front(); q.pop();
                ++sz;
                // up
                if (r > 0 && b[r-1][c] != 0 && !visited[r-1][c] && 
                    (b[r][c] & UP) && (b[r-1][c] & DOWN)) {
                    visited[r-1][c] = true;
                    q.push({r-1, c});
                }
                // down
                if (r+1 < n && b[r+1][c] != 0 && !visited[r+1][c] &&
                    (b[r][c] & DOWN) && (b[r+1][c] & UP)) {
                    visited[r+1][c] = true;
                    q.push({r+1, c});
                }
                // left
                if (c > 0 && b[r][c-1] != 0 && !visited[r][c-1] &&
                    (b[r][c] & LEFT) && (b[r][c-1] & RIGHT)) {
                    visited[r][c-1] = true;
                    q.push({r, c-1});
                }
                // right
                if (c+1 < n && b[r][c+1] != 0 && !visited[r][c+1] &&
                    (b[r][c] & RIGHT) && (b[r][c+1] & LEFT)) {
                    visited[r][c+1] = true;
                    q.push({r, c+1});
                }
            }
            max_comp = max(max_comp, sz);
        }
    }
    return max_comp;
}

// try a move and return new S without modifying board
int try_move(const vector<vector<int>>& b, int er, int ec, int dr, int dc) {
    int nr = er + dr;
    int nc = ec + dc;
    if (nr < 0 || nr >= N || nc < 0 || nc >= N) return -1;
    vector<vector<int>> nb = b;
    swap(nb[er][ec], nb[nr][nc]);
    return compute_S(nb);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> N >> T;
    board.assign(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        string s; cin >> s;
        for (int j = 0; j < N; ++j) {
            board[i][j] = hex_to_int(s[j]);
            if (board[i][j] == 0) {
                empty_r = i;
                empty_c = j;
            }
        }
    }
    
    int current_S = compute_S(board);
    int best_S = current_S;
    string moves = "";
    string best_moves = "";
    int er = empty_r, ec = empty_c;
    
    const double start_temp = 10.0;
    const double end_temp = 0.1;
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.0, 1.0);
    
    const char dirs[4] = {'U', 'D', 'L', 'R'};
    const int dr[4] = {-1, 1, 0, 0};
    const int dc[4] = {0, 0, -1, 1};
    
    for (int step = 0; step < T; ++step) {
        if (current_S == N*N-1) break;
        
        vector<pair<char, int>> candidates; // direction, new_S
        vector<double> weights;
        double total_weight = 0.0;
        
        for (int d = 0; d < 4; ++d) {
            int nr = er + dr[d];
            int nc = ec + dc[d];
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            int new_S = try_move(board, er, ec, dr[d], dc[d]);
            candidates.push_back({dirs[d], new_S});
            double delta = new_S - current_S;
            double temp = start_temp * (1.0 - (double)step/T) + end_temp * ((double)step/T);
            double w = exp(delta / temp);
            weights.push_back(w);
            total_weight += w;
        }
        
        if (candidates.empty()) break;
        
        int chosen;
        if (total_weight < 1e-12) {
            // fallback: choose uniformly
            chosen = rng() % candidates.size();
        } else {
            double r = dist(rng) * total_weight;
            double cum = 0.0;
            for (int i = 0; i < (int)candidates.size(); ++i) {
                cum += weights[i];
                if (r <= cum) {
                    chosen = i;
                    break;
                }
            }
        }
        
        char dir = candidates[chosen].first;
        int new_S_val = candidates[chosen].second;
        int nr = er + dr[chosen];
        int nc = ec + dc[chosen];
        
        // apply move
        swap(board[er][ec], board[nr][nc]);
        er = nr;
        ec = nc;
        current_S = new_S_val;
        moves.push_back(dir);
        
        if (current_S > best_S) {
            best_S = current_S;
            best_moves = moves;
        }
    }
    
    cout << best_moves << endl;
    return 0;
}