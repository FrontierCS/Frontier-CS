#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstring>
#include <random>
#include <chrono>

using namespace std;

const int MAXN = 55;
const int MAXM = 105;

int N, M;
int initial_grid[MAXN][MAXN];
bool required_adj[MAXM][MAXM];

struct State {
    int grid[MAXN][MAXN];
    int edge_counts[MAXM][MAXM];
    int area[MAXM];
    int score;
};

State best_state;
int dr[] = {0, 0, 1, -1};
int dc[] = {1, -1, 0, 0};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

static int visited_token[MAXN][MAXN];
static int token_counter = 0;

bool check_connectivity(int r, int c, int color, int current_grid[MAXN][MAXN], int current_area) {
    if (current_area <= 1) return false;

    int start_r = -1, start_c = -1;
    for (int i = 0; i < 4; i++) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (is_valid(nr, nc) && current_grid[nr][nc] == color) {
            start_r = nr;
            start_c = nc;
            break;
        }
    }

    if (start_r == -1) return false;

    token_counter++;
    static int q_r[MAXN * MAXN], q_c[MAXN * MAXN];
    int head = 0, tail = 0;

    q_r[tail] = start_r;
    q_c[tail] = start_c;
    tail++;
    visited_token[start_r][start_c] = token_counter;

    int count = 1;
    while(head < tail) {
        int cr = q_r[head];
        int cc = q_c[head];
        head++;

        for(int i=0; i<4; i++) {
            int nr = cr + dr[i];
            int nc = cc + dc[i];
            if(is_valid(nr, nc)) {
                if(nr == r && nc == c) continue; 
                if(current_grid[nr][nc] == color && visited_token[nr][nc] != token_counter) {
                    visited_token[nr][nc] = token_counter;
                    q_r[tail] = nr;
                    q_c[tail] = nc;
                    tail++;
                    count++;
                }
            }
        }
    }

    return count == (current_area - 1);
}

void compute_initial_state(State& s) {
    memcpy(s.grid, initial_grid, sizeof(initial_grid));
    memset(s.edge_counts, 0, sizeof(s.edge_counts));
    memset(s.area, 0, sizeof(s.area));
    s.score = 0;

    for(int r=0; r<N; r++) {
        for(int c=0; c<N; c++) {
            int color = s.grid[r][c];
            s.area[color]++;
            if (color == 0) s.score++;

            for(int i=0; i<4; i++) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if(is_valid(nr, nc)) {
                    int n_color = s.grid[nr][nc];
                    s.edge_counts[color][n_color]++;
                } else {
                    s.edge_counts[color][0]++;
                }
            }
        }
    }
}

void solve(double time_limit, const chrono::steady_clock::time_point& start_time, mt19937& rng) {
    State current;
    compute_initial_state(current);

    vector<pair<int, int>> candidates;
    for(int r=0; r<N; r++) {
        for(int c=0; c<N; c++) {
            bool adj0 = false;
            for(int i=0; i<4; i++) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if(!is_valid(nr, nc) || current.grid[nr][nc] == 0) {
                    adj0 = true;
                    break;
                }
            }
            if(adj0 && current.grid[r][c] != 0) {
                candidates.push_back({r, c});
            }
        }
    }

    bool changed = true;
    while(changed) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(now - start_time).count();
        if(elapsed > time_limit) break;

        changed = false;
        shuffle(candidates.begin(), candidates.end(), rng);
        vector<pair<int, int>> kept_candidates;

        for(auto p : candidates) {
            int r = p.first;
            int c = p.second;
            int color = current.grid[r][c];

            if(color == 0) continue; 
            if(current.area[color] <= 1) {
                kept_candidates.push_back(p);
                continue;
            }

            bool possible = true;
            bool exposes_unallowed = false;

            for(int i=0; i<4; i++) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                int n_color = 0;
                if(is_valid(nr, nc)) n_color = current.grid[nr][nc];

                if (n_color != 0 && n_color != color) {
                     if(!required_adj[n_color][0]) {
                         exposes_unallowed = true;
                         break;
                     }
                }
            }

            if(exposes_unallowed) {
                kept_candidates.push_back(p);
                continue;
            }

            static int local_counts[MAXM];
            vector<int> neigh_colors;
            for(int i=0; i<4; i++) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                int n_color = 0;
                if(is_valid(nr, nc)) n_color = current.grid[nr][nc];
                
                if(n_color != color) {
                    if(local_counts[n_color] == 0) neigh_colors.push_back(n_color);
                    local_counts[n_color]++;
                }
            }

            for(int nc_val : neigh_colors) {
                if(required_adj[color][nc_val]) {
                    if(current.edge_counts[color][nc_val] <= local_counts[nc_val]) {
                        possible = false;
                        break;
                    }
                }
                local_counts[nc_val] = 0; 
            }
            if(!possible) {
                kept_candidates.push_back(p);
                continue;
            }

            if(!check_connectivity(r, c, color, current.grid, current.area[color])) {
                kept_candidates.push_back(p);
                continue;
            }

            current.grid[r][c] = 0;
            current.area[color]--;
            current.score++;
            changed = true;

            for(int i=0; i<4; i++) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                int n_color = 0;
                if(is_valid(nr, nc)) n_color = current.grid[nr][nc];

                current.edge_counts[color][n_color]--;
                current.edge_counts[n_color][color]--;
                current.edge_counts[0][n_color]++;
                current.edge_counts[n_color][0]++;

                if(n_color != 0) {
                    kept_candidates.push_back({nr, nc});
                }
            }
        }

        if(changed) {
            sort(kept_candidates.begin(), kept_candidates.end());
            kept_candidates.erase(unique(kept_candidates.begin(), kept_candidates.end()), kept_candidates.end());
            candidates = kept_candidates;
        }
    }

    if(current.score > best_state.score) {
        best_state = current;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if(!(cin >> N >> M)) return 0;
    
    memset(required_adj, 0, sizeof(required_adj));
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            cin >> initial_grid[i][j];
        }
    }

    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            int c1 = initial_grid[i][j];
            
            for(int k=0; k<4; k++) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                int c2 = 0;
                if(is_valid(ni, nj)) c2 = initial_grid[ni][nj];
                
                if(c1 != c2) {
                    required_adj[c1][c2] = true;
                    required_adj[c2][c1] = true;
                }
            }
        }
    }

    auto start_time = chrono::steady_clock::now();
    best_state.score = -1;
    mt19937 rng(123);

    while(true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(now - start_time).count();
        if(elapsed > 1.85) break;
        
        solve(1.85, start_time, rng);
    }

    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            cout << best_state.grid[i][j] << (j == N-1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}