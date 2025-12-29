#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <bitset>
#include <set>

using namespace std;

const int MAXNM = 905;
int N, M;
string grid[35];
int sr, sc, er, ec;
int start_pos, end_pos;

// Directions: L, R, U, D
int dr[] = {0, 0, -1, 1};
int dc[] = {-1, 1, 0, 0};
char dchar[] = {'L', 'R', 'U', 'D'};

int to_id(int r, int c) {
    return r * M + c;
}

pair<int, int> to_rc(int id) {
    return {id / M, id % M};
}

int move_sim(int u, int dir) {
    auto [r, c] = to_rc(u);
    int nr = r + dr[dir];
    int nc = c + dc[dir];
    if (nr >= 0 && nr < N && nc >= 0 && nc < M && grid[nr][nc] == '1') {
        return to_id(nr, nc);
    }
    return u;
}

vector<int> preds[MAXNM][4];
int dist_mat[MAXNM][MAXNM];

struct LightNode {
    int parent_idx;
    int dir;
};

struct FullNode {
    int u;
    bitset<MAXNM> mask;
    int parent_idx; 
    int score; // Lower is better
    
    bool operator<(const FullNode& other) const {
        return score < other.score;
    }
};

vector<vector<LightNode>> history;

string reconstruct(int layer_idx, int node_idx) {
    string res = "";
    while (layer_idx > 0) {
        LightNode node = history[layer_idx][node_idx];
        res += dchar[node.dir];
        node_idx = node.parent_idx;
        layer_idx--;
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    for (int i = 0; i < N; ++i) cin >> grid[i];
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;
    start_pos = to_id(sr, sc);
    end_pos = to_id(er, ec);

    // Build Preds
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < M; ++c) {
            if (grid[r][c] == '0') continue;
            int u = to_id(r, c);
            for (int k = 0; k < 4; ++k) {
                int v = move_sim(u, k);
                preds[v][k].push_back(u);
            }
        }
    }

    // Precompute APSP
    for(int i=0; i<N*M; ++i) for(int j=0; j<N*M; ++j) dist_mat[i][j] = 1e9;
    
    for(int r=0; r<N; ++r){
        for(int c=0; c<M; ++c){
            if(grid[r][c]=='0') continue;
            int u = to_id(r, c);
            dist_mat[u][u] = 0;
            queue<int> q;
            q.push(u);
            while(!q.empty()){
                int curr = q.front(); q.pop();
                int cd = dist_mat[u][curr];
                for(int k=0; k<4; ++k){
                    int nxt = move_sim(curr, k);
                    if(dist_mat[u][nxt] > cd + 1){
                        dist_mat[u][nxt] = cd + 1;
                        q.push(nxt);
                    }
                }
            }
        }
    }

    // Phase 1: Beam Search
    vector<FullNode> current_layer;
    bitset<MAXNM> init_mask;
    init_mask.set(end_pos);
    
    current_layer.push_back({start_pos, init_mask, -1, 0});
    history.push_back({{ -1, -1 }});

    string A = "";
    bool found = false;
    int final_layer = -1, final_node_idx = -1;
    bitset<MAXNM> final_mask;

    if (start_pos == end_pos && init_mask.test(start_pos)) {
        found = true;
        final_layer = 0;
        final_node_idx = 0;
        final_mask = init_mask;
    }

    int beam_width = 1500;
    int max_depth = 2500;

    for (int d = 0; d < max_depth && !found; ++d) {
        if (current_layer.empty()) break;
        
        vector<FullNode> candidates;
        candidates.reserve(current_layer.size() * 4);

        // To deduplicate: set of (u) is not enough, mask matters.
        // But mask is large. We can use simplified dedup or just rely on beam sort.
        // Using a visited array [u] -> best_score could help pruning?
        // But different masks are valid.
        // We will just generate and sort.
        
        for (int i = 0; i < (int)current_layer.size(); ++i) {
            int u = current_layer[i].u;
            const bitset<MAXNM>& curr_mask = current_layer[i].mask;

            for (int k = 0; k < 4; ++k) {
                int v = move_sim(u, k);
                
                bitset<MAXNM> next_mask;
                for (int p = curr_mask._Find_first(); p < MAXNM; p = curr_mask._Find_next(p)) {
                     for(int pred : preds[p][k]) {
                         next_mask.set(pred);
                     }
                }

                if (next_mask.none()) continue;

                if (next_mask.test(v)) {
                    found = true;
                    // Prepare history for next layer to record this move
                    history.push_back({}); 
                    // We only need to push this one node to history to reconstruct
                    history[d+1].push_back({i, k});
                    final_layer = d + 1;
                    final_node_idx = 0;
                    final_mask = next_mask;
                    goto end_phase1;
                }

                // Heuristic
                int min_d = 1e9;
                for (int p = next_mask._Find_first(); p < MAXNM; p = next_mask._Find_next(p)) {
                    if (dist_mat[v][p] < min_d) min_d = dist_mat[v][p];
                }
                
                candidates.push_back({v, next_mask, i, min_d}); // temporarily store 'i' as parent, 'k' not stored yet
                // We need to store 'k' somewhere? 
                // FullNode doesn't have 'dir'. 
                // We can encode dir in parent_idx for candidates? No.
                // Let's use a struct for candidates
            }
        }

        // Refined Candidate Structure for sorting
        struct Candidate {
            int u;
            int parent_idx;
            int dir;
            int score;
            bitset<MAXNM> mask;
            bool operator<(const Candidate& o) const { return score < o.score; }
        };
        vector<Candidate> cands;
        cands.reserve(candidates.size());
        
        // Re-loop to fill cands properly (since loop above was simplified logic)
        // Actually merge loops
        cands.clear();
        for (int i = 0; i < (int)current_layer.size(); ++i) {
            int u = current_layer[i].u;
            const bitset<MAXNM>& curr_mask = current_layer[i].mask;
            for (int k = 0; k < 4; ++k) {
                int v = move_sim(u, k);
                bitset<MAXNM> next_mask;
                for (int p = curr_mask._Find_first(); p < MAXNM; p = curr_mask._Find_next(p)) {
                     for(int pred : preds[p][k]) next_mask.set(pred);
                }
                if (next_mask.none()) continue;
                if (next_mask.test(v)) {
                    found = true;
                    history.push_back({});
                    history[d+1].push_back({i, k});
                    final_layer = d + 1;
                    final_node_idx = 0;
                    final_mask = next_mask;
                    goto end_phase1;
                }
                int min_d = 1e9;
                for (int p = next_mask._Find_first(); p < MAXNM; p = next_mask._Find_next(p)) {
                    if (dist_mat[v][p] < min_d) min_d = dist_mat[v][p];
                }
                cands.push_back({v, i, k, min_d, next_mask});
            }
        }

        if (cands.empty()) break;
        sort(cands.begin(), cands.end());

        // Deduplicate: (u, mask)
        // Since mask is large, maybe skip exact dedup and trust beam?
        // Or dedup by (u, score) roughly.
        // Let's just take top beam_width
        
        vector<FullNode> next_nodes;
        vector<LightNode> next_hist;
        
        int taken = 0;
        // Simple distinct u check to ensure diversity?
        // Let's allow duplicates of u with different masks
        for (const auto& c : cands) {
            if (taken >= beam_width) break;
            next_nodes.push_back({c.u, c.mask, taken, c.score}); // parent in fullnode refers to index in history
            next_hist.push_back({c.parent_idx, c.dir});
            taken++;
        }
        
        current_layer = next_nodes;
        history.push_back(next_hist);
    }

    end_phase1:;

    if (!found && A == "") {
        cout << "-1" << endl;
        return 0;
    }
    
    if (found) {
        A = reconstruct(final_layer, final_node_idx);
    }

    string S_base = A;
    string Ar = A; reverse(Ar.begin(), Ar.end());
    S_base += Ar;

    bitset<MAXNM> visited;
    int t_pos = start_pos;
    visited.set(t_pos);
    for(char c : S_base) {
        int dir=-1; if(c=='L') dir=0; else if(c=='R') dir=1; else if(c=='U') dir=2; else dir=3;
        t_pos = move_sim(t_pos, dir);
        visited.set(t_pos);
    }

    bitset<MAXNM> valid_returns = final_mask; 
    
    // Calculate middle position
    int middle_pos = start_pos;
    for(char c : A) {
        int dir=-1; if(c=='L') dir=0; else if(c=='R') dir=1; else if(c=='U') dir=2; else dir=3;
        middle_pos = move_sim(middle_pos, dir);
    }

    string tour = "";
    vector<int> unvisited;
    
    int iter = 0;
    while(iter < 2000) {
        iter++;
        unvisited.clear();
        for(int r=0; r<N; ++r) for(int c=0; c<M; ++c) {
            if(grid[r][c]=='1') {
                int u = to_id(r,c);
                if(!visited.test(u)) unvisited.push_back(u);
            }
        }
        if(unvisited.empty()) break;

        // BFS to find path to closest unvisited
        queue<pair<int, int>> q;
        q.push({middle_pos, 0});
        vector<int> d(N*M, -1), p_node(N*M, -1), p_dir(N*M, -1);
        d[middle_pos] = 0;
        
        int target = -1;
        while(!q.empty()){
            auto [u, dist] = q.front(); q.pop();
            bool is_unv = false;
            for(int x : unvisited) if(x==u) is_unv=true;
            if(is_unv) { target = u; break; }
            
            for(int k=0; k<4; ++k){
                int v = move_sim(u, k);
                if(d[v] == -1){
                    d[v] = dist+1;
                    p_node[v] = u;
                    p_dir[v] = k;
                    q.push({v, dist+1});
                }
            }
        }

        string P_add = "";
        bool ok = false;

        if (target != -1) {
            string p = "";
            int cur = target;
            while(cur != middle_pos){
                p += dchar[p_dir[cur]];
                cur = p_node[cur];
            }
            reverse(p.begin(), p.end());
            string pr = p; reverse(pr.begin(), pr.end());
            P_add = p + pr;

            // Check if valid
            int sim_curr = middle_pos;
            for(char c : P_add) {
                 int dir=-1; if(c=='L') dir=0; else if(c=='R') dir=1; else if(c=='U') dir=2; else dir=3;
                 sim_curr = move_sim(sim_curr, dir);
            }
            if (valid_returns.test(sim_curr)) {
                ok = true;
                tour += P_add;
                middle_pos = sim_curr;
            }
        }

        if (!ok) {
            // Try small wiggles
            for(int k=0; k<4; ++k){
                string w = ""; w += dchar[k]; w += dchar[k];
                int nxt = middle_pos;
                for(char c : w) {
                    int dir=-1; if(c=='L') dir=0; else if(c=='R') dir=1; else if(c=='U') dir=2; else dir=3;
                    nxt = move_sim(nxt, dir);
                }
                if(valid_returns.test(nxt)){
                    tour += w;
                    middle_pos = nxt;
                    ok = true;
                    break;
                }
            }
        }
        
        // Update visited
        visited.reset();
        t_pos = start_pos;
        visited.set(t_pos);
        string full_S = A + tour + Ar;
        for(char c : full_S) {
            int dir=-1; if(c=='L') dir=0; else if(c=='R') dir=1; else if(c=='U') dir=2; else dir=3;
            t_pos = move_sim(t_pos, dir);
            visited.set(t_pos);
        }
    }

    cout << A << tour << Ar << endl;

    return 0;
}