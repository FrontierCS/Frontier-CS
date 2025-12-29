#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <map>
#include <set>
#include <tuple>

using namespace std;

// State represents the positions of the two virtual particles
struct State {
    int u, v;
};

int N, M;
vector<string> grid;
int sr, sc, er, ec;

// Flatten 2D coordinates to 1D ID
int to_id(int r, int c) {
    return r * M + c;
}

// Convert 1D ID back to 2D coordinates
pair<int, int> to_coord(int id) {
    return {id / M, id % M};
}

// Execute a move for the forward particle
int move_forward(int u, int dir) {
    auto [r, c] = to_coord(u);
    int nr = r, nc = c;
    if (dir == 0) nc--; // L
    else if (dir == 1) nc++; // R
    else if (dir == 2) nr--; // U
    else if (dir == 3) nr++; // D
    
    // Check boundaries and if cell is blank
    if (nr >= 0 && nr < N && nc >= 0 && nc < M && grid[nr][nc] == '1') {
        return to_id(nr, nc);
    }
    return u; // Stay if blocked or out of bounds
}

// Precomputed reverse moves: for each cell and direction, 
// list of cells that move to it via that direction.
vector<int> rev_adj[905][4];

void precompute_rev() {
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < M; c++) {
            if (grid[r][c] == '0') continue;
            int u = to_id(r, c);
            for (int d = 0; d < 4; d++) {
                int v = move_forward(u, d);
                rev_adj[v][d].push_back(u);
            }
        }
    }
}

// BFS variables
// dist[r1][c1][r2][c2] stores the min moves to reach state ((r1,c1), (r2,c2))
short dist[30][30][30][30];

// Parent structure to reconstruct path in the state graph
struct ParentInfo {
    short pr1, pc1, pr2, pc2; // parent state coords
    char move_dir; // move direction index: 0=L, 1=R, 2=U, 3=D
} parent[30][30][30][30];

// Store closest state for each blank cell to ensure coverage
struct CellCover {
    int dist;
    int u, v;
} closest[30][30];

int main() {
    // Optimize I/O
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;
    grid.resize(N);
    int blank_count = 0;
    for (int i = 0; i < N; i++) {
        cin >> grid[i];
        for (char c : grid[i]) if (c == '1') blank_count++;
    }
    cin >> sr >> sc >> er >> ec;
    sr--; sc--; er--; ec--;

    if (blank_count == 0) {
        cout << "-1" << endl;
        return 0;
    }
    
    // Corner case: start and end same, only 1 blank cell -> no moves needed
    if (blank_count == 1 && sr == er && sc == ec) {
        cout << "" << endl;
        return 0;
    }

    precompute_rev();

    // Initialize dist array with -1
    for(int i=0; i<N; ++i)
        for(int j=0; j<M; ++j)
            for(int k=0; k<N; ++k)
                for(int l=0; l<M; ++l)
                    dist[i][j][k][l] = -1;

    // Initialize closest array
    for(int i=0; i<N; ++i)
        for(int j=0; j<M; ++j)
            closest[i][j] = {1000000000, -1, -1};

    queue<State> q;
    State startState = {to_id(sr, sc), to_id(er, ec)};
    dist[sr][sc][er][ec] = 0;
    parent[sr][sc][er][ec] = {-1, -1, -1, -1, -1};
    q.push(startState);

    // Update coverage for start state
    auto update_closest = [&](int r, int c, int d, int u, int v) {
        if (d < closest[r][c].dist) {
            closest[r][c] = {d, u, v};
        }
    };
    update_closest(sr, sc, 0, startState.u, startState.v);
    update_closest(er, ec, 0, startState.u, startState.v);

    // Meeting state candidates
    int best_meet_dist = 1e9;
    State best_meet_state = {-1, -1};
    int meet_type = -1; // 0 for u=v (even len), 1 for u->v (odd len)
    int meet_mid_dir = -1;

    auto check_meet = [&](int u, int v, int d_val) {
        // Type 1: Even length palindrome meeting point
        if (u == v) {
            if (d_val < best_meet_dist) {
                best_meet_dist = d_val;
                best_meet_state = {u, v};
                meet_type = 0;
            }
        }
        // Type 2: Odd length palindrome meeting point
        else {
            if (d_val < best_meet_dist) {
                for(int dir=0; dir<4; ++dir) {
                    if (move_forward(u, dir) == v) {
                        best_meet_dist = d_val;
                        best_meet_state = {u, v};
                        meet_type = 1;
                        meet_mid_dir = dir;
                        return;
                    }
                }
            }
        }
    };

    check_meet(startState.u, startState.v, 0);

    // BFS to explore state space
    while(!q.empty()){
        State curr = q.front();
        q.pop();
        
        auto [r1, c1] = to_coord(curr.u);
        auto [r2, c2] = to_coord(curr.v);
        short d = dist[r1][c1][r2][c2];

        // Try 4 directions
        for(int dir=0; dir<4; ++dir){
            int nu = move_forward(curr.u, dir);
            
            // Reverse move logic for the second particle
            for(int nv : rev_adj[curr.v][dir]) {
                auto [nr1, nc1] = to_coord(nu);
                auto [nr2, nc2] = to_coord(nv);
                
                if (dist[nr1][nc1][nr2][nc2] == -1) {
                    dist[nr1][nc1][nr2][nc2] = d + 1;
                    parent[nr1][nc1][nr2][nc2] = {(short)r1, (short)c1, (short)r2, (short)c2, (char)dir};
                    q.push({nu, nv});
                    
                    update_closest(nr1, nc1, d+1, nu, nv);
                    update_closest(nr2, nc2, d+1, nu, nv);
                    
                    check_meet(nu, nv, d+1);
                }
            }
        }
    }

    if (meet_type == -1) {
        cout << "-1" << endl;
        return 0;
    }

    // Collect key states that cover all blank cells
    vector<State> key_states;
    for(int i=0; i<N; ++i){
        for(int j=0; j<M; ++j){
            if (grid[i][j] == '1') {
                if (closest[i][j].dist > 1e8) {
                    cout << "-1" << endl; // Some blank cell is unreachable
                    return 0;
                }
                key_states.push_back({closest[i][j].u, closest[i][j].v});
            }
        }
    }
    key_states.push_back(best_meet_state);

    // Helper to map state to unique int for building the virtual tree
    auto pack = [&](int r1, int c1, int r2, int c2) {
        return r1 * 27000 + c1 * 900 + r2 * 30 + c2;
    };
    auto unpack = [&](int val) -> tuple<int,int,int,int> {
        int c2 = val % 30; val /= 30;
        int r2 = val % 30; val /= 30;
        int c1 = val % 30; val /= 30;
        int r1 = val;
        return {r1, c1, r2, c2};
    };

    // Build the virtual tree (subtree of the BFS tree)
    map<int, vector<pair<int, int>>> adj; // u -> list of (v, move)
    set<int> added_nodes;
    int root_packed = pack(sr, sc, er, ec);
    int meet_packed = pack(to_coord(best_meet_state.u).first, to_coord(best_meet_state.u).second,
                           to_coord(best_meet_state.v).first, to_coord(best_meet_state.v).second);

    for(auto ks : key_states) {
        auto [kr1, kc1] = to_coord(ks.u);
        auto [kr2, kc2] = to_coord(ks.v);
        int curr = pack(kr1, kc1, kr2, kc2);
        
        while(curr != root_packed) {
            if(added_nodes.count(curr)) break; 
            added_nodes.insert(curr);
            
            auto [cr1, cc1, cr2, cc2] = unpack(curr);
            ParentInfo pi = parent[cr1][cc1][cr2][cc2];
            int p_packed = pack(pi.pr1, pi.pc1, pi.pr2, pi.pc2);
            
            adj[p_packed].push_back({curr, pi.move_dir});
            curr = p_packed;
        }
    }

    // Mark nodes on the path to the meeting state
    map<int, bool> leads_to_meet;
    int temp = meet_packed;
    while(temp != root_packed) {
        leads_to_meet[temp] = true;
        auto [cr1, cc1, cr2, cc2] = unpack(temp);
        ParentInfo pi = parent[cr1][cc1][cr2][cc2];
        if (pi.pr1 == -1) break; // Should be root, safety break
        temp = pack(pi.pr1, pi.pc1, pi.pr2, pi.pc2);
    }
    leads_to_meet[meet_packed] = true;

    string half_str = "";
    string chars = "LRUD";

    // DFS to traverse the virtual tree and build the first half of the palindrome string
    auto dfs = [&](auto&& self, int u) -> void {
        if (u == meet_packed) {
            // Reached meeting point, continue if it has children but treat this branch as special
        }

        vector<pair<int, int>> &neighbors = adj[u];
        pair<int, int> meet_child = {-1, -1};
        vector<pair<int, int>> other_children;
        
        for(auto &edge : neighbors) {
            if (leads_to_meet.count(edge.first)) {
                meet_child = edge;
            } else {
                other_children.push_back(edge);
            }
        }

        // Visit side branches fully
        for(auto &edge : other_children) {
            half_str += chars[edge.second];
            self(self, edge.first);
            half_str += chars[edge.second ^ 1]; // Return move (inverse of L(0)<->R(1), U(2)<->D(3))
        }

        // Proceed towards meeting state
        if (meet_child.first != -1) {
            half_str += chars[meet_child.second];
            self(self, meet_child.first);
        }
    };

    dfs(dfs, root_packed);

    string res = half_str;
    if (meet_type == 1) {
        res += chars[meet_mid_dir];
    }
    string rev_half = half_str;
    reverse(rev_half.begin(), rev_half.end());
    res += rev_half;

    cout << res << endl;

    return 0;
}