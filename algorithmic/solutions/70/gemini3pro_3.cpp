#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <queue>
#include <bitset>

using namespace std;

// Structure to represent a possible state (hypothesis)
struct Hypothesis {
    int u; // current vertex
    bitset<305> visited; // set of visited vertices

    // Equality operator for unique/deduplication
    bool operator==(const Hypothesis& other) const {
        return u == other.u && visited == other.visited;
    }
};

// Comparator for sorting/set to allow efficient deduplication
struct HypCmp {
    bool operator()(const Hypothesis& a, const Hypothesis& b) const {
        if (a.u != b.u) return a.u < b.u;
        // Compare bitsets lexicographically
        for (size_t i = 0; i < 305; ++i) { 
             if (a.visited[i] != b.visited[i]) return a.visited[i] < b.visited[i];
        }
        return false;
    }
};

int n, m, start_node, base_move_count;
vector<int> adj[305];
int degree[305];

void solve() {
    if (!(cin >> n >> m >> start_node >> base_move_count)) return;
    
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
        degree[i] = 0;
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        degree[u]++;
        degree[v]++;
    }

    vector<Hypothesis> hyps;
    Hypothesis start_h;
    start_h.u = start_node;
    start_h.visited.reset();
    start_h.visited[start_node] = 1;
    hyps.push_back(start_h);

    while (true) {
        string token;
        cin >> token;
        if (token == "AC") return; // Completed map
        if (token == "F") return;  // Failed map (should handle gracefully)

        int d_curr = stoi(token);
        vector<pair<int, int>> obs(d_curr);
        for (int i = 0; i < d_curr; ++i) {
            cin >> obs[i].first >> obs[i].second;
        }

        // 1. Filter hypotheses based on observation
        // Also remove hypotheses that claim all nodes are visited (since we didn't get AC)
        vector<Hypothesis> consistent_hyps;
        vector<pair<int, int>> sorted_obs = obs;
        sort(sorted_obs.begin(), sorted_obs.end());

        for (const auto& h : hyps) {
            // If a hypothesis claims we visited all nodes, but we are still playing, it's invalid.
            if (h.visited.count() == n) continue;

            if (degree[h.u] != d_curr) continue;
            
            vector<pair<int, int>> expected;
            for (int v : adj[h.u]) {
                expected.push_back({degree[v], h.visited[v] ? 1 : 0});
            }
            sort(expected.begin(), expected.end());

            if (expected == sorted_obs) {
                consistent_hyps.push_back(h);
            }
        }
        hyps = consistent_hyps;
        
        if (hyps.empty()) {
            // This case implies inconsistency between our tracking and the judge.
            // Should theoretically not happen. Make a random valid move to continue.
            cout << "1" << endl; 
            continue; 
        }

        // 2. Evaluate moves. We want to move towards unvisited nodes.
        // For each hypothesis, calculate distance from neighbors to nearest unvisited node.
        
        struct HypInfo {
            map<int, int> neighbor_dist; 
        };
        vector<HypInfo> h_infos(hyps.size());
        
        for (int i = 0; i < hyps.size(); ++i) {
            const auto& h = hyps[i];
            
            // Multi-source BFS from all unvisited nodes to find distances
            queue<int> q;
            vector<int> dist_to_unvisited(n + 1, 1e9);
            
            for(int v=1; v<=n; ++v) {
                if(!h.visited[v]) {
                    dist_to_unvisited[v] = 0;
                    q.push(v);
                }
            }
            
            while(!q.empty()){
                int curr = q.front();
                q.pop();
                
                for(int neighbor : adj[curr]){
                    if(dist_to_unvisited[neighbor] > dist_to_unvisited[curr] + 1){
                        dist_to_unvisited[neighbor] = dist_to_unvisited[curr] + 1;
                        q.push(neighbor);
                    }
                }
            }
            
            for(int neighbor : adj[h.u]) {
                h_infos[i].neighbor_dist[neighbor] = dist_to_unvisited[neighbor];
            }
        }
        
        // 3. Score each port option
        int best_move_idx = -1;
        double best_score = 1e18; 
        
        for (int i = 0; i < d_curr; ++i) {
            pair<int, int> p = obs[i];
            
            double current_port_score = 0;
            
            for (int j = 0; j < hyps.size(); ++j) {
                const auto& h = hyps[j];
                const auto& info = h_infos[j];
                
                // Find candidates in h.u's neighbors that match property p
                vector<int> candidates;
                for (int v : adj[h.u]) {
                    if (degree[v] == p.first && (h.visited[v] ? 1 : 0) == p.second) {
                        candidates.push_back(v);
                    }
                }
                
                if (candidates.empty()) {
                    current_port_score += 1e9; // Invalid move for this hypothesis?
                    continue;
                }
                
                double sum_dist = 0;
                for (int v : candidates) {
                    sum_dist += info.neighbor_dist.at(v);
                }
                double avg_dist = sum_dist / candidates.size();
                current_port_score += avg_dist;
                
                // Penalty for ambiguity to encourage resolving location
                if (candidates.size() > 1) {
                    current_port_score += 0.5;
                }
            }
            
            if (current_port_score < best_score) {
                best_score = current_port_score;
                best_move_idx = i;
            }
        }
        
        // 4. Output move
        cout << (best_move_idx + 1) << endl;
        
        // 5. Update hypotheses based on the chosen move properties
        vector<Hypothesis> next_hyps;
        pair<int, int> p_chosen = obs[best_move_idx];
        
        for (const auto& h : hyps) {
             for (int v : adj[h.u]) {
                 if (degree[v] == p_chosen.first && (h.visited[v] ? 1 : 0) == p_chosen.second) {
                     Hypothesis new_h = h;
                     new_h.u = v;
                     new_h.visited[v] = 1;
                     next_hyps.push_back(new_h);
                 }
             }
        }
        
        // Deduplicate hypotheses
        sort(next_hyps.begin(), next_hyps.end(), HypCmp());
        auto last = unique(next_hyps.begin(), next_hyps.end(), [](const Hypothesis& a, const Hypothesis& b){
            return a.u == b.u && a.visited == b.visited;
        });
        next_hyps.erase(last, next_hyps.end());
        
        hyps = next_hyps;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}