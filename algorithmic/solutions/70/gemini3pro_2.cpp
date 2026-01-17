#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <queue>
#include <bitset>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 305;
// Limit the number of hypotheses to keep the solution fast. 
// Given the constraints and problem type, ambiguity usually resolves quickly.
const int MAX_HYPS = 150; 

int N, M, Start, BaseMoves;
vector<int> adj[MAXN];
int degree[MAXN];

// Represents a possible state of the world: where we are and what we have visited.
struct Hypothesis {
    int u; // Current vertex
    bitset<MAXN> vis; // Visited mask
    
    // Strict weak ordering for sorting/set
    bool operator<(const Hypothesis& other) const {
        if (u != other.u) return u < other.u;
        // Compare bitsets lexicographically
        for (int i = 1; i <= N; ++i) {
            if (vis[i] != other.vis[i]) {
                // If this->vis[i] is 0 and other.vis[i] is 1, then this < other.
                // return other.vis[i] works because if other is 1, returns true (0 < 1).
                return other.vis[i]; 
            }
        }
        return false;
    }
    
    bool operator==(const Hypothesis& other) const {
        return u == other.u && vis == other.vis;
    }
};

// Structure to hold observation data for a neighbor
struct NeighborObs {
    int d;
    int flag;
    int original_index; // 1-based index in the input line
    
    bool operator<(const NeighborObs& other) const {
        if (d != other.d) return d < other.d;
        return flag < other.flag;
    }
};

void solve_map() {
    if (!(cin >> N >> M >> Start >> BaseMoves)) return;
    
    for (int i = 1; i <= N; ++i) {
        adj[i].clear();
        degree[i] = 0;
    }
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }
    
    // Initial hypothesis: we are at Start, and only Start is visited.
    vector<Hypothesis> hyps;
    Hypothesis start_h;
    start_h.u = Start;
    start_h.vis.reset();
    start_h.vis[Start] = 1;
    hyps.push_back(start_h);
    
    while (true) {
        string token;
        cin >> token;
        if (token == "AC" || token == "F") {
            break;
        }
        
        int cur_deg = stoi(token);
        vector<NeighborObs> obs(cur_deg);
        for (int i = 0; i < cur_deg; ++i) {
            cin >> obs[i].d >> obs[i].flag;
            obs[i].original_index = i + 1;
        }
        
        // Sort obs to create a signature for comparison
        vector<NeighborObs> sorted_obs = obs;
        sort(sorted_obs.begin(), sorted_obs.end());
        
        // 1. Filter Hypotheses
        // Remove hypotheses that are inconsistent with the current observation.
        vector<Hypothesis> valid_hyps;
        valid_hyps.reserve(hyps.size());
        
        for (const auto& h : hyps) {
            if (degree[h.u] != cur_deg) continue;
            
            // Generate expected neighbor signature from the graph structure and hypothesis state
            vector<pair<int, int>> expected;
            expected.reserve(cur_deg);
            for (int v : adj[h.u]) {
                expected.push_back({degree[v], (int)h.vis[v]});
            }
            sort(expected.begin(), expected.end());
            
            // Compare expected signature with observed signature
            bool match = true;
            for (int i = 0; i < cur_deg; ++i) {
                if (expected[i].first != sorted_obs[i].d || 
                    expected[i].second != sorted_obs[i].flag) {
                    match = false;
                    break;
                }
            }
            if (match) {
                valid_hyps.push_back(h);
            }
        }
        
        hyps = valid_hyps;
        if (hyps.empty()) {
            // This implies all hypotheses were wrong. Should not happen if logic is correct.
            return; 
        }
        
        // 2. Choose Move
        // We use the first hypothesis (the "leader") to make a decision.
        // We perform a BFS to find the nearest unvisited node according to the leader.
        const Hypothesis& leader = hyps[0];
        
        int next_node = -1;
        
        // BFS
        queue<int> q;
        q.push(leader.u);
        vector<int> dist(N + 1, -1);
        vector<int> parent(N + 1, 0);
        dist[leader.u] = 0;
        
        int found_target = -1;
        
        while(!q.empty()){
            int u = q.front(); q.pop();
            if (!leader.vis[u]) {
                found_target = u;
                break;
            }
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
        
        if (found_target != -1) {
            // Reconstruct the first step of the path
            int curr = found_target;
            while(parent[curr] != leader.u && parent[curr] != 0) {
                curr = parent[curr];
            }
            next_node = curr;
        } else {
            // If all nodes appear visited in this hypothesis, move to any neighbor
            if (!adj[leader.u].empty()) next_node = adj[leader.u][0];
        }
        
        // Determine signature of the edge to next_node
        int desired_d = degree[next_node];
        int desired_f = leader.vis[next_node];
        
        // Find which index in the observation matches these properties.
        int chosen_idx = -1;
        for (const auto& o : obs) {
            if (o.d == desired_d && o.flag == desired_f) {
                chosen_idx = o.original_index;
                break; // Pick the first match
            }
        }
        
        cout << chosen_idx << endl;
        
        // 3. Update Hypotheses for the next step
        // For each hypothesis, any neighbor that matches the chosen edge properties is a possible next state.
        vector<Hypothesis> next_gen_hyps;
        next_gen_hyps.reserve(hyps.size() * 2);
        
        for (const auto& h : hyps) {
            for (int v : adj[h.u]) {
                if (degree[v] == desired_d && (int)h.vis[v] == desired_f) {
                    Hypothesis nh = h;
                    nh.u = v;
                    nh.vis[v] = 1; // Mark the new node as visited
                    next_gen_hyps.push_back(nh);
                }
            }
        }
        
        // Prune duplicates to keep the set small
        sort(next_gen_hyps.begin(), next_gen_hyps.end());
        next_gen_hyps.erase(unique(next_gen_hyps.begin(), next_gen_hyps.end()), next_gen_hyps.end());
        
        // Limit the number of hypotheses to avoid TLE/MLE
        if (next_gen_hyps.size() > MAX_HYPS) {
            next_gen_hyps.resize(MAX_HYPS);
        }
        hyps = next_gen_hyps;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve_map();
        }
    }
    return 0;
}