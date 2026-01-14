#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <set>
#include <queue>
#include <map>

using namespace std;

struct Edge {
    int to;
};

int N, M, Start, BaseMoves;
vector<vector<int>> adj;
vector<int> degree;
vector<bool> visited_global; // My belief of visited vertices (definitely visited)
int total_visited_count = 0;

struct NeighborObs {
    int deg;
    int flag;
    // For sorting/comparison
    bool operator<(const NeighborObs& other) const {
        if (deg != other.deg) return deg < other.deg;
        return flag < other.flag;
    }
    bool operator==(const NeighborObs& other) const {
        return deg == other.deg && flag == other.flag;
    }
};

// Check if a candidate vertex u is consistent with the observation
// Obs: degree of current node, and list of (deg, flag) for neighbors
bool is_consistent(int u, int obs_deg, const vector<NeighborObs>& obs_neighbors) {
    if (degree[u] != obs_deg) return false;

    // Group observations by degree
    // Group memory neighbors by degree
    
    // Construct mem_neighbors from known graph and visited status
    vector<NeighborObs> mem_neighbors;
    for (int v : adj[u]) {
        mem_neighbors.push_back({degree[v], visited_global[v] ? 1 : 0});
    }
    sort(mem_neighbors.begin(), mem_neighbors.end());

    // obs_neighbors is assumed sorted by degree then flag.
    if (mem_neighbors.size() != obs_neighbors.size()) return false;

    size_t ptr = 0;
    while (ptr < mem_neighbors.size()) {
        int current_deg = mem_neighbors[ptr].deg;
        
        int mem_start = ptr;
        while (ptr < mem_neighbors.size() && mem_neighbors[ptr].deg == current_deg) ptr++;
        int mem_end = ptr;
        
        int obs_start = mem_start;
        // Check if obs degrees match
        if (obs_start >= obs_neighbors.size() || obs_neighbors[obs_start].deg != current_deg) return false;
        
        int ptr_obs = obs_start;
        while (ptr_obs < obs_neighbors.size() && obs_neighbors[ptr_obs].deg == current_deg) ptr_obs++;
        int obs_end = ptr_obs;
        
        if ((mem_end - mem_start) != (obs_end - obs_start)) return false;

        // Now check flags for this block of same degree neighbors
        // Condition: count(1 in mem) <= count(1 in obs).
        
        int mem_ones = 0;
        for (int i = mem_start; i < mem_end; ++i) if (mem_neighbors[i].flag == 1) mem_ones++;
        
        int obs_ones = 0;
        for (int i = obs_start; i < obs_end; ++i) if (obs_neighbors[i].flag == 1) obs_ones++;
        
        if (mem_ones > obs_ones) return false;
    }
    
    return true;
}

void solve() {
    if (!(cin >> N >> M >> Start >> BaseMoves)) return;
    adj.assign(N + 1, vector<int>());
    degree.assign(N + 1, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    visited_global.assign(N + 1, false);
    total_visited_count = 0;
    
    vector<int> candidates;
    candidates.push_back(Start);
    
    while (true) {
        // 1. Read input
        string line_start;
        if (!(cin >> line_start)) break;
        if (line_start == "AC") return; 
        if (line_start == "F") return; 

        int obs_deg = stoi(line_start);
        vector<NeighborObs> obs_neighbors(obs_deg);
        for (int i = 0; i < obs_deg; ++i) {
            cin >> obs_neighbors[i].deg >> obs_neighbors[i].flag;
        }

        // 2. Filter candidates
        vector<int> next_candidates_filtered;
        vector<NeighborObs> sorted_obs = obs_neighbors;
        sort(sorted_obs.begin(), sorted_obs.end());

        for (int u : candidates) {
            if (is_consistent(u, obs_deg, sorted_obs)) {
                next_candidates_filtered.push_back(u);
            }
        }
        candidates = next_candidates_filtered;

        if (candidates.empty()) {
            candidates.push_back(1); // Should not happen
        }

        // 3. Mark visited if unique
        if (candidates.size() == 1) {
            int u = candidates[0];
            if (!visited_global[u]) {
                visited_global[u] = true;
                total_visited_count++;
            }
        }

        // 4. Plan move
        vector<int> dist(N + 1, 1e9);
        vector<int> parent(N + 1, 0);
        queue<int> q;
        for (int u : candidates) {
            dist[u] = 0;
            parent[u] = 0;
            q.push(u);
        }

        int target = -1;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            
            if (!visited_global[u]) {
                target = u;
                break;
            }

            for (int v : adj[u]) {
                if (dist[v] == 1e9) {
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }

        if (target == -1) {
            // Fallback move
            cout << 1 << endl;
            // Update candidates blindly
            vector<int> next_cands;
            for(int u : candidates) {
                for(int v : adj[u]) {
                     if (degree[v] == obs_neighbors[0].deg) {
                         int flag = obs_neighbors[0].flag;
                         bool vis = visited_global[v];
                         if (flag == 1 || (flag == 0 && !vis)) {
                             next_cands.push_back(v);
                         }
                     }
                }
            }
            sort(next_cands.begin(), next_cands.end());
            next_cands.erase(unique(next_cands.begin(), next_cands.end()), next_cands.end());
            candidates = next_cands;
            continue;
        }

        int next_node = -1;
        if (dist[target] == 0) {
            // We are possibly at target, move to any neighbor
            next_node = adj[candidates[0]][0];
        } else {
            int curr = target;
            while (dist[curr] > 1) {
                curr = parent[curr];
            }
            next_node = curr;
        }

        int expected_deg = degree[next_node];
        int expected_flag = visited_global[next_node] ? 1 : 0;
        
        int best_idx = -1;
        // Exact match
        for (int i = 0; i < obs_deg; ++i) {
            if (obs_neighbors[i].deg == expected_deg && obs_neighbors[i].flag == expected_flag) {
                best_idx = i;
                break;
            }
        }
        // Weak match
        if (best_idx == -1 && expected_flag == 0) {
            for (int i = 0; i < obs_deg; ++i) {
                if (obs_neighbors[i].deg == expected_deg && obs_neighbors[i].flag == 1) {
                    best_idx = i;
                    break;
                }
            }
        }
        if (best_idx == -1) best_idx = 0;

        cout << (best_idx + 1) << endl;

        // 5. Update candidates
        vector<int> next_cands;
        NeighborObs move_obs = obs_neighbors[best_idx];
        
        for (int u : candidates) {
            for (int v : adj[u]) {
                if (degree[v] == move_obs.deg) {
                    bool v_vis = visited_global[v];
                    int flag = move_obs.flag;
                    if (flag == 0 && v_vis) continue; 
                    next_cands.push_back(v);
                }
            }
        }
        sort(next_cands.begin(), next_cands.end());
        next_cands.erase(unique(next_cands.begin(), next_cands.end()), next_cands.end());
        candidates = next_cands;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}