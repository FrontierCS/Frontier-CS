#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <random>
#include <map>
#include <bitset>
#include <ctime>

using namespace std;

// Maximum number of blank cells
const int MAX_CELLS = 905;

int N, M;
vector<string> grid;
int SR, SC, ER, EC;
int total_blanks = 0;
int cell_id[35][35];
pair<int,int> id_to_cell[MAX_CELLS];

// Adjacency lists
int fwd_move[MAX_CELLS][4]; // 0:L, 1:R, 2:U, 3:D
vector<int> bwd_move[MAX_CELLS][4]; // Inverse moves

// Directions: L, R, U, D
int dr[] = {0, 0, -1, 1}; 
int dc[] = {-1, 1, 0, 0};
string DIR_CHARS = "LRUD";

typedef bitset<MAX_CELLS> Mask;

bool is_valid(int r, int c) {
    return r >= 1 && r <= N && c >= 1 && c <= M && grid[r-1][c-1] == '1';
}

// Compute the set of possible previous positions given a current set and a move direction
Mask get_inv_mask(const Mask& current, int dir) {
    Mask next_m;
    if (current.none()) return next_m;
    // Optimization: iterate only set bits? 
    // std::bitset doesn't support easy iteration. 
    // Given MAX_CELLS=900, a loop is fast enough (900 iterations is tiny).
    for (int i = 0; i < total_blanks; ++i) {
        if (current.test(i)) {
            for (int prev : bwd_move[i][dir]) {
                next_m.set(prev);
            }
        }
    }
    return next_m;
}

// Check if all blank cells are reachable from start
void check_connectivity() {
    queue<int> q;
    vector<bool> vis(total_blanks, false);
    int start_node = cell_id[SR][SC];
    q.push(start_node);
    vis[start_node] = true;
    int cnt = 0;
    while(!q.empty()){
        int u = q.front(); q.pop();
        cnt++;
        for(int d=0; d<4; ++d){
            int v = fwd_move[u][d];
            if(!vis[v]){
                vis[v] = true;
                q.push(v);
            }
        }
    }
    // Note: total_blanks includes all '1's. If the component of start 
    // is smaller than total_blanks, we can't visit all.
    // Also, End must be reachable, which is implied if component covers all.
    if (cnt != total_blanks) {
        cout << "-1" << endl;
        exit(0);
    }
}

struct State {
    int u;
    Mask mask;
    // Custom comparator for map
    bool operator<(const State& o) const {
        if (u != o.u) return u < o.u;
        for (int i = 0; i < total_blanks; ++i) {
             bool b1 = mask[i];
             bool b2 = o.mask[i];
             if (b1 != b2) return b1 < b2;
        }
        return false;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    srand((unsigned)time(0));

    if (!(cin >> N >> M)) return 0;
    grid.resize(N);
    for(int i=0; i<N; ++i) cin >> grid[i];
    cin >> SR >> SC >> ER >> EC;

    int id_counter = 0;
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=M; ++j) {
            if (grid[i-1][j-1] == '1') {
                cell_id[i][j] = id_counter;
                id_to_cell[id_counter] = {i, j};
                id_counter++;
            } else {
                cell_id[i][j] = -1;
            }
        }
    }
    total_blanks = id_counter;

    // Precompute moves graph
    for(int u=0; u<total_blanks; ++u) {
        auto [r, c] = id_to_cell[u];
        for(int d=0; d<4; ++d) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            int v_id = u; // Default stay if blocked/out
            if (is_valid(nr, nc)) {
                v_id = cell_id[nr][nc];
            }
            fwd_move[u][d] = v_id;
            bwd_move[v_id][d].push_back(u);
        }
    }

    check_connectivity();

    // Corner case: already at end with 1 cell
    if (total_blanks == 1 && SR == ER && SC == EC) {
        cout << "" << endl;
        return 0;
    }

    int start_node = cell_id[SR][SC];
    int end_node = cell_id[ER][EC];

    double time_limit = 0.95;
    clock_t start_clock = clock();

    while ((double)(clock() - start_clock) / CLOCKS_PER_SEC < time_limit) {
        // Phase 1: Randomized Greedy Walk
        // Goal: Visit all nodes while maintaining a non-empty set V of possible backward positions
        string path = "";
        int curr = start_node;
        Mask V; 
        V.set(end_node);
        Mask visited;
        visited.set(curr);
        
        bool phase1_success = true;
        int steps = 0;
        int max_steps = 3000; // Sufficient for 30x30 grid

        while (visited.count() < total_blanks) {
            if (steps > max_steps) {
                 phase1_success = false;
                 break;
            }
            
            vector<int> candidates;
            vector<int> priorities;
            
            for(int d=0; d<4; ++d) {
                Mask next_V = get_inv_mask(V, d);
                if (next_V.any()) {
                    candidates.push_back(d);
                    int next_u = fwd_move[curr][d];
                    int score = 0;
                    if (!visited.test(next_u)) score += 100; // Prefer unvisited
                    // Tie-break with randomness
                    priorities.push_back(score + (rand() % 50));
                }
            }

            if (candidates.empty()) {
                phase1_success = false;
                break;
            }

            int best_idx = -1;
            int best_prio = -1;
            for(size_t i=0; i<candidates.size(); ++i) {
                if (priorities[i] > best_prio) {
                    best_prio = priorities[i];
                    best_idx = i;
                }
            }
            
            int d = candidates[best_idx];
            curr = fwd_move[curr][d];
            V = get_inv_mask(V, d);
            path += DIR_CHARS[d];
            visited.set(curr);
            steps++;
        }

        if (!phase1_success) continue;

        // Phase 2: BFS to connect 'curr' to 'V'
        // Check immediate match (even length palindrome P + P^R)
        if (V.test(curr)) {
             string rev_path = path;
             reverse(rev_path.begin(), rev_path.end());
             cout << path + rev_path << endl;
             return 0;
        }
        // Check immediate match (odd length palindrome P + d + P^R)
        for(int d=0; d<4; ++d) {
            if (V.test(fwd_move[curr][d])) {
                 string rev_path = path;
                 reverse(rev_path.begin(), rev_path.end());
                 cout << path + DIR_CHARS[d] + rev_path << endl;
                 return 0;
            }
        }

        // BFS
        queue<pair<State, string>> q;
        q.push({{curr, V}, ""});
        
        map<State, int> seen;
        seen[{curr, V}] = 0;

        int bfs_limit = 10000;
        int bfs_cnt = 0;

        while(!q.empty()) {
            auto [st, p] = q.front(); q.pop();
            bfs_cnt++;
            if (bfs_cnt > bfs_limit) break;

            // Check if any move connects to V (odd length solution)
            for(int d=0; d<4; ++d) {
                int nxt_u = fwd_move[st.u][d];
                if (st.mask.test(nxt_u)) {
                    // Solution: path + p + d + (path + p)^R
                    string full_p = path + p;
                    string mid = ""; mid += DIR_CHARS[d];
                    string rev_p = full_p;
                    reverse(rev_p.begin(), rev_p.end());
                    cout << full_p + mid + rev_p << endl;
                    return 0;
                }
            }
            
            // Try extending path (for even length solution)
            for(int d=0; d<4; ++d) {
                int nxt_u = fwd_move[st.u][d];
                Mask nxt_mask = get_inv_mask(st.mask, d);
                
                if (nxt_mask.none()) continue;
                
                // Check if new state is a meeting point
                if (nxt_mask.test(nxt_u)) {
                     // Solution: path + p + d + (path + p + d)^R
                     string full_p = path + p + DIR_CHARS[d];
                     string rev_p = full_p;
                     reverse(rev_p.begin(), rev_p.end());
                     cout << full_p + rev_p << endl;
                     return 0;
                }
                
                State nxt_st = {nxt_u, nxt_mask};
                if (seen.find(nxt_st) == seen.end()) {
                    seen[nxt_st] = (int)p.length() + 1;
                    q.push({nxt_st, p + DIR_CHARS[d]});
                }
            }
        }
    }
    
    cout << "-1" << endl;
    return 0;
}