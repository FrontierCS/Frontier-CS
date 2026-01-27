#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Maximum constraints
const int MAXN = 10005;
const int MAXM = 500005;

struct Edge {
    int u, v;
};

int N, M;
Edge edges[MAXM];
vector<int> adj[MAXN]; 

// Solution State
bool in_cover[MAXN];
int cov_count[MAXM]; // Number of covered endpoints: 0, 1, 2
int dscore[MAXN];    // Heuristic score: improvement in uncovered edges count

// Uncovered edges management
int uncov_edges[MAXM];
int uncov_pos[MAXM]; // Position in uncov_edges array
int uncov_cnt = 0;

void add_uncov(int eid) {
    if (uncov_pos[eid] != -1) return;
    uncov_edges[uncov_cnt] = eid;
    uncov_pos[eid] = uncov_cnt;
    uncov_cnt++;
}

void remove_uncov(int eid) {
    if (uncov_pos[eid] == -1) return;
    int last_eid = uncov_edges[uncov_cnt - 1];
    int pos = uncov_pos[eid];
    
    uncov_edges[pos] = last_eid;
    uncov_pos[last_eid] = pos;
    
    uncov_pos[eid] = -1;
    uncov_cnt--;
}

// Cover set management
int cover_list[MAXN];
int pos_in_cover[MAXN];
int cover_size = 0;

void add_to_cover_list(int v) {
    if (pos_in_cover[v] != -1) return;
    cover_list[cover_size] = v;
    pos_in_cover[v] = cover_size;
    cover_size++;
}

void remove_from_cover_list(int v) {
    if (pos_in_cover[v] == -1) return;
    int last = cover_list[cover_size - 1];
    int pos = pos_in_cover[v];
    
    cover_list[pos] = last;
    pos_in_cover[last] = pos;
    
    pos_in_cover[v] = -1;
    cover_size--;
}

// Flip vertex status and update scores
void flip(int v) {
    in_cover[v] = !in_cover[v];
    
    int dscore_v = 0;
    
    for (int eid : adj[v]) {
        int u = (edges[eid].u == v) ? edges[eid].v : edges[eid].u;
        
        int old_cov = cov_count[eid];
        int new_cov = old_cov + (in_cover[v] ? 1 : -1);
        cov_count[eid] = new_cov;
        
        // Update neighbors' dscore based on edge coverage change
        if (old_cov == 0 && new_cov == 1) {
            remove_uncov(eid);
            dscore[u]--; 
        } else if (old_cov == 1 && new_cov == 0) {
            add_uncov(eid);
            dscore[u]++;
        } else if (old_cov == 1 && new_cov == 2) {
            dscore[u]++;
        } else if (old_cov == 2 && new_cov == 1) {
            dscore[u]--;
        }
        
        // Accumulate dscore for v itself
        if (in_cover[v]) {
            // v is IN. dscore measures loss if removed (negative)
            if (new_cov == 1) dscore_v--;
        } else {
            // v is OUT. dscore measures gain if added (positive)
            if (new_cov == 0) dscore_v++;
        }
    }
    dscore[v] = dscore_v;
}

void flip_with_list(int v) {
    bool was_in = in_cover[v];
    flip(v);
    if (!was_in) add_to_cover_list(v);
    else remove_from_cover_list(v);
}

void build_dscores() {
    for (int i = 1; i <= N; ++i) dscore[i] = 0;
    for (int i = 1; i <= N; ++i) {
        for (int eid : adj[i]) {
            if (in_cover[i]) {
                if (cov_count[eid] == 1) dscore[i]--;
            } else {
                if (cov_count[eid] == 0) dscore[i]++;
            }
        }
    }
}

long long steps = 0;
long long conf_change[MAXN];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(42); 

    if (!(cin >> N >> M)) return 0;
    
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v;
        adj[edges[i].u].push_back(i);
        adj[edges[i].v].push_back(i);
        cov_count[i] = 0;
    }
    
    // Arrays init
    fill(in_cover, in_cover + N + 1, false);
    fill(pos_in_cover, pos_in_cover + N + 1, -1);
    fill(uncov_pos, uncov_pos + M, -1);
    fill(conf_change, conf_change + N + 1, 0);
    
    // 1. Greedy Initial Construction
    // Uses highest dynamic degree heuristic
    vector<int> dyn_degree(N + 1, 0);
    for(int i=0; i<M; ++i) {
        dyn_degree[edges[i].u]++;
        dyn_degree[edges[i].v]++;
    }
    
    vector<bool> edge_covered(M, false);
    int covered_cnt = 0;
    
    while (covered_cnt < M) {
        int best_v = -1;
        int max_deg = -1;
        
        // Linear scan for max degree (O(N) per step is acceptable given N=10000)
        for (int i=1; i<=N; ++i) {
            if (!in_cover[i] && dyn_degree[i] > max_deg) {
                max_deg = dyn_degree[i];
                best_v = i;
            }
        }
        
        if (best_v == -1 || max_deg == 0) break;
        
        in_cover[best_v] = true;
        add_to_cover_list(best_v);
        
        for (int eid : adj[best_v]) {
            if (!edge_covered[eid]) {
                edge_covered[eid] = true;
                covered_cnt++;
                int other = (edges[eid].u == best_v) ? edges[eid].v : edges[eid].u;
                dyn_degree[other]--;
            }
        }
        dyn_degree[best_v] = 0;
    }
    
    // Rebuild proper state structures
    uncov_cnt = 0;
    for (int i=0; i<M; ++i) {
        int c = 0;
        if (in_cover[edges[i].u]) c++;
        if (in_cover[edges[i].v]) c++;
        cov_count[i] = c;
        if (c == 0) add_uncov(i);
    }
    build_dscores();
    
    // 2. Prune redundancies
    {
        vector<int> temp_list;
        for(int i=0; i<cover_size; ++i) temp_list.push_back(cover_list[i]);
        for(int v : temp_list) {
            if(in_cover[v] && dscore[v] == 0) flip_with_list(v);
        }
    }
    
    vector<int> best_sol;
    for(int i=1; i<=N; ++i) if(in_cover[i]) best_sol.push_back(i);
    
    // 3. Local Search Loop
    double time_limit = 1.95;
    
    while (true) {
        if ((double)clock() / CLOCKS_PER_SEC > time_limit) break;
        
        // Strategy: Reduce size by 1 (remove best candidate) and try to resolve conflicts
        int rem_cand = -1;
        int max_ds = -1000000;
        
        // Sample for removal (approximation of best)
        for (int k=0; k<50; ++k) {
            int idx = rand() % cover_size;
            int v = cover_list[idx];
            if (dscore[v] > max_ds) {
                max_ds = dscore[v];
                rem_cand = v;
            }
        }
        if (rem_cand == -1 && cover_size > 0) rem_cand = cover_list[rand() % cover_size];
        
        if (rem_cand != -1) {
            flip_with_list(rem_cand);
            conf_change[rem_cand] = steps;
        }
        
        bool solved = false;
        long long iter_limit = 2000; // Search depth limit per reduction
        
        for (long long iter = 0; iter < iter_limit; ++iter) {
            if (uncov_cnt == 0) {
                solved = true;
                break;
            }
            if ((double)clock() / CLOCKS_PER_SEC > time_limit) break;
            
            // Pick an uncovered edge
            int rand_idx = rand() % uncov_cnt;
            int eid = uncov_edges[rand_idx];
            int u = edges[eid].u;
            int v = edges[eid].v;
            
            int to_add = u;
            // Heuristic to pick endpoint
            if (dscore[v] > dscore[u]) to_add = v;
            else if (dscore[u] == dscore[v] && (rand() & 1)) to_add = v;
            
            // Tabu mechanism: avoid recently flipped
            if (conf_change[u] > conf_change[v]) to_add = v; 
            else if (conf_change[v] > conf_change[u]) to_add = u;
            
            flip_with_list(to_add);
            conf_change[to_add] = steps + iter;
            
            // We increased size, now remove one to maintain size (NuMVC inspired sway)
            int best_drop = -1;
            int best_drop_val = -1000000;
            
            // BMS for removal candidate
            for (int k=0; k<15; ++k) {
                int idx = rand() % cover_size;
                int cand = cover_list[idx];
                if (cand == to_add) continue; 
                
                if (dscore[cand] > best_drop_val) {
                    best_drop_val = dscore[cand];
                    best_drop = cand;
                }
            }
            if (best_drop != -1) {
                flip_with_list(best_drop);
                conf_change[best_drop] = steps + iter;
            }
        }
        
        steps += iter_limit;
        
        if (solved) {
            // Found a smaller cover
            // Prune redundancies from this new solution
            {
                for(int i=0; i<cover_size; ++i) {
                    int v = cover_list[i];
                    if(dscore[v] == 0) {
                        flip_with_list(v);
                        i--;
                    }
                }
            }
            best_sol.clear();
            for(int i=1; i<=N; ++i) if(in_cover[i]) best_sol.push_back(i);
        } else {
            // Failed to find smaller cover, revert to best known
            fill(in_cover, in_cover + N + 1, false);
            fill(pos_in_cover, pos_in_cover + N + 1, -1);
            cover_size = 0;
            for (int v : best_sol) {
                in_cover[v] = true;
                add_to_cover_list(v);
            }
            // Rebuild auxiliary structures
            uncov_cnt = 0;
            fill(uncov_pos, uncov_pos + M, -1);
            for (int i=0; i<M; ++i) {
                int c = 0;
                if (in_cover[edges[i].u]) c++;
                if (in_cover[edges[i].v]) c++;
                cov_count[i] = c;
                if (c == 0) add_uncov(i);
            }
            build_dscores();
        }
    }
    
    // Output
    vector<int> out(N + 1, 0);
    for (int v : best_sol) out[v] = 1;
    for (int i = 1; i <= N; ++i) cout << out[i] << "\n";
    
    return 0;
}