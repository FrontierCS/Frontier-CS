#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <bitset>

using namespace std;

const int MAXN = 30;
// Max states is N*M * N*M, roughly 900*900 = 810,000.
const int MAX_STATES = 30 * 30 * 30 * 30; 

int N, M;
string grid[MAXN];
int SR, SC, ER, EC;
int blank_cells_count = 0;
vector<pair<int, int>> blank_cells;
int cell_id[MAXN][MAXN];
pair<int, int> id_cell[MAXN * MAXN];

// Directions: 0:L, 1:R, 2:U, 3:D
int dr[] = {0, 0, -1, 1};
int dc[] = {-1, 1, 0, 0};
char dir_char[] = {'L', 'R', 'U', 'D'};

int move_table[MAXN * MAXN][4];
vector<int> pre_move[MAXN * MAXN][4];

// BFS related arrays
int dist_to_meet[MAX_STATES]; // Stores minimum steps to reach a meeting state in state graph (reverse direction)
int bfs_vis[MAX_STATES];
int bfs_gen = 0;
int parent_state[MAX_STATES]; // for path reconstruction in greedy step
int parent_move[MAX_STATES];

bool is_blank(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < M && grid[r][c] == '1';
}

void precompute() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            // For blocked cells, they act as walls or non-destinations.
            // But 'move' is from a blank cell. If it hits '0', it stays.
            // We only care about moves FROM blank cells.
            if (grid[i][j] == '0') continue;
            int u = cell_id[i][j];
            for (int d = 0; d < 4; ++d) {
                int nr = i + dr[d];
                int nc = j + dc[d];
                int v = u; // Default stay
                if (is_blank(nr, nc)) {
                    v = cell_id[nr][nc];
                }
                move_table[u][d] = v;
                pre_move[v][d].push_back(u);
            }
        }
    }
}

// Encode/Decode state
inline int encode(int u, int v) {
    return u * (N * M) + v;
}
inline pair<int, int> decode(int s) {
    return {s / (N * M), s % (N * M)};
}

// Compute valid states that can reach a palindrome center
void compute_valid_states() {
    for(int i=0; i<MAX_STATES; ++i) dist_to_meet[i] = -1;
    
    queue<int> q;
    
    // Initialize with meeting states
    for (auto p : blank_cells) {
        int u = cell_id[p.first][p.second];
        // Type 1: u == v (Even length palindrome meeting point)
        int s = encode(u, u);
        if (dist_to_meet[s] == -1) {
            dist_to_meet[s] = 0;
            q.push(s);
        }
        
        // Type 2: adjacent via some move d (Odd length palindrome center)
        // u -> d -> v implies move(u, d) == v
        // In the state graph, reaching (u, v) allows finishing with move d.
        for (int d = 0; d < 4; ++d) {
            int v = move_table[u][d];
            int s2 = encode(u, v);
            if (dist_to_meet[s2] == -1) {
                dist_to_meet[s2] = 0; 
                q.push(s2);
            }
        }
    }

    // Reverse BFS to find all states that can reach a meeting state
    while (!q.empty()) {
        int s = q.front();
        q.pop();
        auto [u_curr, v_curr] = decode(s);
        
        // We look for predecessors (u_prev, v_prev) such that
        // (u_prev, v_prev) --d--> (u_curr, v_curr)
        // This means: move(u_prev, d) == u_curr AND move(v_curr, d) == v_prev
        // Note the asymmetry: v moves backwards in the palindrome construction process,
        // but in the state graph transition logic we derived: 
        // Forward State Transition: (u, v) --d--> (move(u, d), v') where move(v', d) = v.
        // So here we are reversing that edge.
        // We want (u_prev, v_prev) such that u_curr = move(u_prev, d) and v_prev = move(v_curr, d).
        
        for (int d = 0; d < 4; ++d) {
            // v_prev is deterministically determined from v_curr
            int v_prev = move_table[v_curr][d];
            // u_prev can be any cell that moves to u_curr with direction d
            for (int u_prev : pre_move[u_curr][d]) {
                int s_prev = encode(u_prev, v_prev);
                if (dist_to_meet[s_prev] == -1) {
                    dist_to_meet[s_prev] = dist_to_meet[s] + 1;
                    q.push(s_prev);
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    for (int i = 0; i < N; ++i) cin >> grid[i];
    cin >> SR >> SC >> ER >> EC;
    SR--; SC--; ER--; EC--;

    int cnt = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            cell_id[i][j] = cnt;
            id_cell[cnt] = {i, j};
            if (grid[i][j] == '1') {
                blank_cells.push_back({i, j});
            }
            cnt++;
        }
    }
    blank_cells_count = blank_cells.size();

    precompute();
    compute_valid_states();

    int start_u = cell_id[SR][SC];
    int start_v = cell_id[ER][EC];
    int start_state = encode(start_u, start_v);

    if (dist_to_meet[start_state] == -1) {
        cout << "-1" << endl;
        return 0;
    }

    vector<bool> visited_cell(N * M, false);
    int visited_count = 0;
    // Mark blocked cells as already visited (we only count blank ones)
    for(int i=0; i<N*M; ++i) {
        auto [r, c] = id_cell[i];
        if(grid[r][c] == '0') visited_cell[i] = true;
    }
    // Initially visited start and end cells
    if (!visited_cell[start_u]) { visited_cell[start_u] = true; visited_count++; }
    if (!visited_cell[start_v]) { visited_cell[start_v] = true; visited_count++; }

    string first_half = "";
    int current_state = start_state;

    // Greedy strategy: repeatedly find path to nearest unvisited cell
    while (visited_count < blank_cells_count) {
        bfs_gen++;
        queue<int> q;
        q.push(current_state);
        bfs_vis[current_state] = bfs_gen;
        parent_state[current_state] = -1;
        
        int found_state = -1;
        
        while(!q.empty()){
            int s = q.front();
            q.pop();
            
            auto [u, v] = decode(s);
            // Check if this state helps visit a new cell
            if ((!visited_cell[u] && grid[id_cell[u].first][id_cell[u].second] == '1') || 
                (!visited_cell[v] && grid[id_cell[v].first][id_cell[v].second] == '1')) {
                found_state = s;
                break;
            }
            
            // Try neighbors in state graph
            for(int d=0; d<4; ++d){
                int nu = move_table[u][d];
                // For v, we need nv such that move(nv, d) = v
                for(int nv : pre_move[v][d]){
                    int ns = encode(nu, nv);
                    // Must be a valid state (can reach meeting) and not visited in this BFS
                    if(dist_to_meet[ns] != -1 && bfs_vis[ns] != bfs_gen){
                        bfs_vis[ns] = bfs_gen;
                        parent_state[ns] = s;
                        parent_move[ns] = d;
                        q.push(ns);
                    }
                }
            }
        }
        
        if (found_state == -1) {
            cout << "-1" << endl;
            return 0;
        }
        
        // Reconstruct path segment
        string segment = "";
        vector<int> path_states;
        int curr = found_state;
        while(curr != current_state){
            path_states.push_back(curr);
            segment += dir_char[parent_move[curr]];
            curr = parent_state[curr];
        }
        reverse(segment.begin(), segment.end());
        reverse(path_states.begin(), path_states.end());
        
        first_half += segment;
        
        // Update visited along the path
        for(int s : path_states){
            auto [u, v] = decode(s);
            if (!visited_cell[u]) { visited_cell[u] = true; visited_count++; }
            if (!visited_cell[v]) { visited_cell[v] = true; visited_count++; }
        }
        current_state = found_state;
    }
    
    // After visiting all cells, find path to nearest meeting state
    bfs_gen++;
    queue<int> q;
    q.push(current_state);
    bfs_vis[current_state] = bfs_gen;
    parent_state[current_state] = -1;
    
    int meet_state = -1;
    
    // Check if current is already meet
    auto [cu, cv] = decode(current_state);
    if(cu == cv) meet_state = current_state;
    else {
        for(int d=0; d<4; ++d){
            if(move_table[cu][d] == cv) {
                meet_state = current_state;
                break;
            }
        }
    }
    
    if (meet_state == -1) {
        while(!q.empty()){
            int s = q.front();
            q.pop();
            
            auto [u, v] = decode(s);
            // Check meet condition
            bool met = (u == v);
            if(!met){
                for(int d=0; d<4; ++d) if(move_table[u][d] == v) met = true;
            }
            if(met){
                meet_state = s;
                break;
            }
            
            for(int d=0; d<4; ++d){
                int nu = move_table[u][d];
                for(int nv : pre_move[v][d]){
                    int ns = encode(nu, nv);
                    if(dist_to_meet[ns] != -1 && bfs_vis[ns] != bfs_gen){
                        bfs_vis[ns] = bfs_gen;
                        parent_state[ns] = s;
                        parent_move[ns] = d;
                        q.push(ns);
                    }
                }
            }
        }
    }
    
    if (meet_state == -1) {
        cout << "-1" << endl;
        return 0;
    }
    
    string segment = "";
    int curr = meet_state;
    while(curr != current_state){
        segment += dir_char[parent_move[curr]];
        curr = parent_state[curr];
    }
    reverse(segment.begin(), segment.end());
    first_half += segment;
    
    // Construct final palindrome
    string ans = first_half;
    auto [mu, mv] = decode(meet_state);
    string middle = "";
    if (mu != mv) {
        // Find d such that move(mu, d) == mv
        for(int d=0; d<4; ++d){
            if(move_table[mu][d] == mv){
                middle += dir_char[d];
                break;
            }
        }
    }
    
    string rev = first_half;
    reverse(rev.begin(), rev.end());
    cout << ans << middle << rev << endl;

    return 0;
}