#include <iostream>
#include <vector>
#include <deque>
#include <algorithm>
#include <queue>
#include <tuple>

using namespace std;

// Structure to represent a position in the grid
struct Pos {
    int r, c;
    bool operator<(const Pos& other) const {
        return tie(r, c) < tie(other.r, other.c);
    }
    bool operator==(const Pos& other) const {
        return tie(r, c) == tie(other.r, other.c);
    }
};

// Global variables for problem data
int n, m;
int G[505][505];
Pos valPos[250005]; // Value -> Position mapping
int dist[505][505]; // BFS distance array

// Priority queue to maintain the m smallest values found so far
priority_queue<int> pq;

// Function to update the set of smallest values
void update_pq(int val) {
    pq.push(val);
    if (pq.size() > m) {
        pq.pop();
    }
}

// Get the current threshold (m-th smallest value)
int get_threshold() {
    if (pq.size() < m) return 250005; // Effectively infinity
    return pq.top();
}

// State representing a possible snake configuration
struct State {
    deque<Pos> body;
};

void solve() {
    cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> G[i][j];
            valPos[G[i][j]] = {i, j};
        }
    }

    // Reset priority queue for new test case
    while (!pq.empty()) pq.pop();

    // Iterate through each snake length l
    for (int l = 1; l <= n; ++l) {
        // Optimization: Check if it's possible for snake of length l to cover only small values
        int threshold = get_threshold();
        int cnt = 0;
        
        // Count how many values in the grid are strictly smaller than the threshold
        if (threshold > n * n) cnt = n * n;
        else cnt = threshold - 1;

        // If the number of small values is less than snake length, 
        // the max value covered by the snake MUST be >= threshold.
        // Since we only care about values smaller than threshold, we can skip.
        if (l > cnt) {
            break; 
        }

        // Initialize possible states for snake of length l
        // At T=1, snake is at [(1,1), (1,2), ..., (1,l)] with head at (1,1)
        vector<State> states;
        State initial_state;
        for (int k = 1; k <= l; ++k) {
            initial_state.body.push_back({1, k});
        }
        states.push_back(initial_state);

        bool active = true;

        for (int T = 1; T <= 2 * n - 1; ++T) {
            if (states.empty()) break; 

            // Pruning: Check reachability to interesting values
            threshold = get_threshold();
            
            // Identify target cells (values < threshold)
            vector<Pos> targets;
            int limit = (threshold > n * n) ? n * n : threshold - 1;
            for(int v = 1; v <= limit; ++v) targets.push_back(valPos[v]);
            
            // If no targets exist and we have enough values, stop.
            if (targets.empty() && pq.size() == m) {
                active = false; 
                break;
            }

            // BFS to find shortest distance from any target to current heads
            // We compute distance on the grid using reverse moves (Up/Left)
            for(int i=1; i<=n; ++i) for(int j=1; j<=n; ++j) dist[i][j] = -1;
            
            queue<Pos> q;
            for(const auto& p : targets) {
                dist[p.r][p.c] = 0;
                q.push(p);
            }
            
            while(!q.empty()){
                Pos u = q.front(); q.pop();
                // Reverse moves: Up (-1, 0), Left (0, -1)
                int dr[] = {-1, 0};
                int dc[] = {0, -1};
                for(int k=0; k<2; ++k){
                    int nr = u.r + dr[k];
                    int nc = u.c + dc[k];
                    if(nr >= 1 && nr <= n && nc >= 1 && nc <= n && dist[nr][nc] == -1){
                        dist[nr][nc] = dist[u.r][u.c] + 1;
                        q.push({nr, nc});
                    }
                }
            }

            // Filter states that cannot reach any target in remaining time
            bool possible = false;
            for(const auto& st : states) {
                Pos head = st.body.front();
                int d = dist[head.r][head.c];
                int remaining_steps = (2 * n - 1) - T;
                if (d != -1 && d <= remaining_steps) {
                    possible = true;
                }
            }

            if (!possible) {
                active = false;
                break;
            }

            // Perform Query
            cout << "? " << l << " " << T << endl;
            int val;
            cin >> val;
            update_pq(val);

            // Filter states consistent with observed value
            vector<State> next_states;
            vector<State> consistent_states;

            for(const auto& st : states) {
                int max_v = 0;
                for(const auto& p : st.body) max_v = max(max_v, G[p.r][p.c]);
                if (max_v == val) {
                    consistent_states.push_back(st);
                }
            }
            
            states = consistent_states;
            if (states.empty()) break; 

            if (T == 2 * n - 1) break; 

            // Advance states: Try moving Down and Right
            // At T=1 (move to T=2), only Down allowed.
            next_states.clear();
            for(const auto& st : states) {
                Pos head = st.body.front();
                vector<Pos> candidates;
                if (T == 1) {
                    candidates.push_back({head.r + 1, head.c});
                } else {
                    candidates.push_back({head.r + 1, head.c});
                    candidates.push_back({head.r, head.c + 1});
                }

                for(auto next_head : candidates) {
                    if (next_head.r <= n && next_head.c <= n) {
                        State nst = st;
                        nst.body.push_front(next_head);
                        nst.body.pop_back();
                        next_states.push_back(nst);
                    }
                }
            }
            
            // Limit the number of states to avoid TLE/MLE
            if (next_states.size() > 50) {
                 // Keep states with heads closest to targets
                 vector<pair<int, int>> scored;
                 for(int i=0; i<next_states.size(); ++i) {
                     Pos h = next_states[i].body.front();
                     int d = dist[h.r][h.c];
                     if (d == -1) d = 1e9;
                     scored.push_back({d, i});
                 }
                 sort(scored.begin(), scored.end());
                 vector<State> pruned;
                 for(int i=0; i<min((int)next_states.size(), 50); ++i) {
                     pruned.push_back(next_states[scored[i].second]);
                 }
                 states = pruned;
            } else {
                states = next_states;
            }
        }
    }

    // Output answer
    vector<int> ans;
    while(!pq.empty()){
        ans.push_back(pq.top());
        pq.pop();
    }
    sort(ans.begin(), ans.end());
    cout << "!";
    for(int x : ans) cout << " " << x;
    cout << endl;
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