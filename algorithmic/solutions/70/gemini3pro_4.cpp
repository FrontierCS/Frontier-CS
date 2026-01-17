#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <bitset>
#include <string>

using namespace std;

// Global variables to store graph structure for current test case
int N, M, Start, BaseMoves;
vector<vector<int>> adj;

// State representation: current vertex and the set of visited vertices
struct State {
    int u;
    bitset<305> visited;
};

// Function to compare states for sorting/uniqueness
bool compareStates(const State& a, const State& b) {
    if (a.u != b.u) return a.u < b.u;
    for (int i = 1; i <= N; ++i) {
        bool bitA = a.visited[i];
        bool bitB = b.visited[i];
        if (bitA != bitB) return bitA < bitB;
    }
    return false;
}

// Function to check equality of states
bool areStatesEqual(const State& a, const State& b) {
    return a.u == b.u && a.visited == b.visited;
}

void solve_map() {
    if (!(cin >> N >> M >> Start >> BaseMoves)) return;

    adj.assign(N + 1, vector<int>());
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Initial state: we are at Start, and Start is visited
    vector<State> states;
    bitset<305> init_visited;
    init_visited[Start] = 1;
    states.push_back({Start, init_visited});

    while (true) {
        string token;
        cin >> token;
        if (token == "AC") {
            // Map solved successfully
            return;
        }
        if (token == "F") {
            // Failed map (move limit exceeded)
            return;
        }

        // Parse observation
        int d = stoi(token);
        vector<pair<int, int>> obs_neighbors(d);
        for (int i = 0; i < d; ++i) {
            cin >> obs_neighbors[i].first >> obs_neighbors[i].second;
        }

        // Sort observation for multiset comparison later
        vector<pair<int, int>> sorted_obs = obs_neighbors;
        sort(sorted_obs.begin(), sorted_obs.end());

        // 1. Filter states consistent with the current observation
        vector<State> consistent_states;
        consistent_states.reserve(states.size());
        for (const auto& s : states) {
            // Basic degree check
            if ((int)adj[s.u].size() != d) continue;

            // Neighborhood signature check
            // The signature consists of pairs (degree of neighbor, visited status of neighbor)
            vector<pair<int, int>> profile;
            profile.reserve(d);
            for (int v : adj[s.u]) {
                profile.push_back({(int)adj[v].size(), (int)s.visited[v]});
            }
            sort(profile.begin(), profile.end());

            if (profile == sorted_obs) {
                consistent_states.push_back(s);
            }
        }
        states = consistent_states;

        // If states empty, it implies logic error or inconsistency, but we proceed
        if (states.empty()) {
            // Should not happen with correct logic
        }

        // 2. Plan Move: Vote for the best edge index
        // index_scores[i] stores the score of choosing the i-th option (0-based)
        vector<double> index_scores(d, 0.0);

        for (const auto& s : states) {
            // BFS to find the nearest unvisited node from s.u
            queue<int> q;
            q.push(s.u);
            vector<int> dist(N + 1, -1);
            vector<int> parent(N + 1, 0);
            dist[s.u] = 0;
            
            int target = -1;
            
            // If not all nodes are visited in this state hypothesis
            // Note: count() returns number of set bits. 
            // We only use bits 1..N. Bit 0 is 0.
            if (s.visited.count() < (size_t)N) {
                 while (!q.empty()) {
                    int u = q.front(); q.pop();
                    if (!s.visited[u]) {
                        target = u;
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
            }
            
            if (target != -1) {
                // Trace back to find the immediate neighbor (next step)
                int curr = target;
                while (parent[curr] != 0 && parent[curr] != s.u) {
                    curr = parent[curr];
                }
                int next_step = curr;
                
                // Properties of the desired neighbor
                int desired_deg = adj[next_step].size();
                int desired_vis = s.visited[next_step];
                
                // Find indices in the current observation that match these properties
                int match_count = 0;
                for (int i = 0; i < d; ++i) {
                    if (obs_neighbors[i].first == desired_deg && obs_neighbors[i].second == desired_vis) {
                        match_count++;
                    }
                }
                
                // Distribute vote among matching indices
                if (match_count > 0) {
                    double vote = 1.0 / match_count;
                    for (int i = 0; i < d; ++i) {
                        if (obs_neighbors[i].first == desired_deg && obs_neighbors[i].second == desired_vis) {
                            index_scores[i] += vote;
                        }
                    }
                }
            } else {
                // If no target found (e.g. all visited according to this state), spread votes uniformly
                for (int i = 0; i < d; ++i) index_scores[i] += 1.0/d;
            }
        }

        // Select the index with the highest score
        int best_idx = 0;
        double max_score = -1.0;
        for (int i = 0; i < d; ++i) {
            if (index_scores[i] > max_score + 1e-9) {
                max_score = index_scores[i];
                best_idx = i;
            }
        }

        // Output choice (1-based index)
        cout << best_idx + 1 << endl;

        // 3. Predict next states based on the chosen move
        int chosen_d = obs_neighbors[best_idx].first;
        int chosen_f = obs_neighbors[best_idx].second;

        vector<State> next_states;
        next_states.reserve(states.size() * 2); // heuristic reserve
        for (const auto& s : states) {
            for (int v : adj[s.u]) {
                // A valid destination must match the properties of the chosen edge
                if ((int)adj[v].size() == chosen_d && (int)s.visited[v] == chosen_f) {
                    State ns = s;
                    ns.u = v;
                    ns.visited[v] = 1; // Mark the new vertex as visited
                    next_states.push_back(ns);
                }
            }
        }

        // Remove duplicates to keep the set of states manageable
        sort(next_states.begin(), next_states.end(), compareStates);
        next_states.erase(unique(next_states.begin(), next_states.end(), areStatesEqual), next_states.end());

        states = next_states;
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    if (cin >> t) {
        while (t--) {
            solve_map();
        }
    }
    return 0;
}