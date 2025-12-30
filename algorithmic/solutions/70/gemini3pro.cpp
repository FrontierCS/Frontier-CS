#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <queue>
#include <bitset>
#include <map>
#include <set>
#include <cmath>

using namespace std;

const int MAXN = 305;

struct State {
    int u;
    bitset<MAXN> visited;
    
    // Determine order for set/sorting
    bool operator<(const State& other) const {
        if (u != other.u) return u < other.u;
        for (int i = 0; i < MAXN; ++i) {
            if (visited[i] != other.visited[i]) return other.visited[i]; 
        }
        return false;
    }
    bool operator==(const State& other) const {
        return u == other.u && visited == other.visited;
    }
};

int N, M, Start, BaseMoveCount;
vector<int> adj[MAXN];

// Observation data
struct NeighborObs {
    int deg;
    int flag;
};
vector<NeighborObs> current_obs;

// Helper to get degree of a node
int get_deg(int u) {
    return adj[u].size();
}

// Helper to generate signature for a state
// Returns sorted list of pairs (deg, flag)
vector<pair<int, int>> get_signature(const State& s) {
    vector<pair<int, int>> sig;
    sig.reserve(adj[s.u].size());
    for (int v : adj[s.u]) {
        int d = get_deg(v);
        int f = s.visited[v] ? 1 : 0;
        sig.push_back({d, f});
    }
    sort(sig.begin(), sig.end());
    return sig;
}

// BFS to find nearest unvisited node from state s
// Returns pair: distance, next_hop_neighbor_index_in_adj
// If all visited, returns {-1, -1}
pair<int, int> get_target(const State& s) {
    // Check if everything is visited
    if (s.visited.count() == N) return {-1, -1};

    queue<pair<int, int>> q;
    // dist array to keep track of visited in BFS
    // Initialize with -1
    vector<int> dist(N + 1, -1);
    
    dist[s.u] = 0;
    
    // We want to find the first step towards the nearest unvisited node.
    // Initialize queue with neighbors of s.u
    for (int v : adj[s.u]) {
        if (dist[v] == -1) {
            dist[v] = 1;
            // Check if v itself is unvisited
            if (!s.visited[v]) return {1, v};
            q.push({v, v}); // Stores {current_node, first_step_node}
        }
    }
    
    while(!q.empty()) {
        auto [u, first_step] = q.front();
        q.pop();
        
        // If we found an unvisited node (BFS layer by layer ensures nearest)
        if (!s.visited[u]) {
            return {dist[u], first_step};
        }
        
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push({v, first_step});
            }
        }
    }
    return {-1, -1};
}

void solve() {
    if (!(cin >> N >> M >> Start >> BaseMoveCount)) return;
    
    for (int i = 1; i <= N; ++i) adj[i].clear();
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    vector<State> states;
    State initial;
    initial.u = Start;
    initial.visited.reset();
    initial.visited[Start] = 1;
    states.push_back(initial);
    
    while (true) {
        string token;
        cin >> token;
        if (token == "AC") return;
        if (token == "F") return; 
        
        int d = stoi(token);
        current_obs.clear();
        current_obs.resize(d);
        
        // Map to count occurrences of each type in observation
        map<pair<int,int>, int> obs_counts;
        
        for (int i = 0; i < d; ++i) {
            cin >> current_obs[i].deg >> current_obs[i].flag;
            obs_counts[{current_obs[i].deg, current_obs[i].flag}]++;
        }
        
        // Filter states: keep only those consistent with current observation
        vector<State> next_states_filter;
        next_states_filter.reserve(states.size());
        
        for (const auto& s : states) {
            if (adj[s.u].size() != d) continue;
            
            vector<pair<int, int>> sig = get_signature(s);
            map<pair<int,int>, int> sig_counts;
            for(auto p : sig) sig_counts[p]++;
            
            if (sig_counts == obs_counts) {
                next_states_filter.push_back(s);
            }
        }
        
        states = next_states_filter;
        if (states.empty()) return; // Should not happen
        
        // Prune states if too many to avoid TLE/MLE
        if (states.size() > 150) {
            states.resize(150);
        }
        
        // Vote for next move type (degree, flag)
        map<pair<int,int>, int> votes;
        
        for (const auto& s : states) {
            pair<int, int> res = get_target(s);
            if (res.first != -1) {
                int next_v = res.second;
                int deg_v = get_deg(next_v);
                int flag_v = s.visited[next_v] ? 1 : 0;
                votes[{deg_v, flag_v}]++;
            } else {
                // If this state thinks all visited, try to pick any neighbor
                if (!adj[s.u].empty()) {
                    int next_v = adj[s.u][0];
                    int deg_v = get_deg(next_v);
                    int flag_v = s.visited[next_v] ? 1 : 0;
                    votes[{deg_v, flag_v}]++;
                }
            }
        }
        
        // Pick best type that exists in observation
        pair<int, int> best_type = {-1, -1};
        int max_vote = -1;
        
        for (auto const& [type, count] : votes) {
            if (obs_counts.find(type) != obs_counts.end()) {
                if (count > max_vote) {
                    max_vote = count;
                    best_type = type;
                }
            }
        }
        
        // Fallback if votes don't match observation (should be rare/impossible if consistent)
        if (best_type.first == -1) {
             best_type = {current_obs[0].deg, current_obs[0].flag};
        }
        
        // Find index of best_type in the current observation list
        int move_idx = -1;
        for (int i = 0; i < d; ++i) {
            if (current_obs[i].deg == best_type.first && current_obs[i].flag == best_type.second) {
                move_idx = i + 1; // 1-based index
                break;
            }
        }
        
        cout << move_idx << endl;
        
        // Update states based on the chosen move type
        vector<State> next_step_states;
        next_step_states.reserve(states.size() * 2); 
        
        for (const auto& s : states) {
            // Find all neighbors of s.u that match the chosen (deg, flag)
            for (int v : adj[s.u]) {
                int dv = get_deg(v);
                int fv = s.visited[v] ? 1 : 0;
                if (dv == best_type.first && fv == best_type.second) {
                    State ns = s;
                    ns.u = v;
                    ns.visited[v] = 1;
                    next_step_states.push_back(ns);
                }
            }
        }
        
        // Deduplicate states
        sort(next_step_states.begin(), next_step_states.end());
        next_step_states.erase(unique(next_step_states.begin(), next_step_states.end()), next_step_states.end());
        
        states = next_step_states;
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