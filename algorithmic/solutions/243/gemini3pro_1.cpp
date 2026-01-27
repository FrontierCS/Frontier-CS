#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Represents a possible state of the user: position (r, c) and direction facing
struct State {
    int r, c, dir; // 0: N, 1: E, 2: S, 3: W
    int id;
};

int R, C;
vector<string> grid;
vector<State> states;
// Mapping from (r, c, dir) to state ID
int state_grid[105][105][4]; 
// Properties indexed by state ID
int wall_dist[40005];
int next_state[40005][3]; // 0: L, 1: R, 2: Step. -1 if invalid
int ec_class[40005]; // Equivalence class ID

int dr[] = {-1, 0, 1, 0};
int dc[] = {0, 1, 0, -1};

// Helper to compute distance to wall
int get_wall_dist(int r, int c, int dir) {
    int d = 0;
    while (true) {
        int nr = r + dr[dir];
        int nc = c + dc[dir];
        if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc] == '#') {
            return d;
        }
        r = nr;
        c = nc;
        d++;
    }
}

// Initialization of states and transitions
void init() {
    int id_counter = 0;
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '.') {
                for (int d = 0; d < 4; ++d) {
                    state_grid[r][c][d] = id_counter;
                    states.push_back({r, c, d, id_counter});
                    id_counter++;
                }
            }
        }
    }

    for (const auto& s : states) {
        wall_dist[s.id] = get_wall_dist(s.r, s.c, s.dir);
        
        // Left turn: (dir + 3) % 4
        int ld = (s.dir + 3) % 4;
        next_state[s.id][0] = state_grid[s.r][s.c][ld];
        
        // Right turn: (dir + 1) % 4
        int rd = (s.dir + 1) % 4;
        next_state[s.id][1] = state_grid[s.r][s.c][rd];
        
        // Step forward: valid only if wall_dist > 0
        if (wall_dist[s.id] > 0) {
            int nr = s.r + dr[s.dir];
            int nc = s.c + dc[s.dir];
            next_state[s.id][2] = state_grid[nr][nc][s.dir];
        } else {
            next_state[s.id][2] = -1;
        }
    }
}

// Compute equivalence classes to detect indistinguishable states
void compute_equivalence() {
    int num_states = states.size();
    for (int i = 0; i < num_states; ++i) ec_class[i] = wall_dist[i];
    
    bool changed = true;
    while (changed) {
        changed = false;
        vector<pair<vector<int>, int>> sigs(num_states);
        for (int i = 0; i < num_states; ++i) {
            vector<int> sig;
            sig.push_back(ec_class[i]);
            // Neighbors via Left, Right, Step
            sig.push_back(ec_class[next_state[i][0]]);
            sig.push_back(ec_class[next_state[i][1]]);
            if (next_state[i][2] != -1) {
                sig.push_back(ec_class[next_state[i][2]]);
            } else {
                sig.push_back(-1);
            }
            sigs[i] = {sig, i};
        }
        sort(sigs.begin(), sigs.end());
        
        int new_c = 0;
        vector<int> new_classes(num_states);
        for (int i = 0; i < num_states; ++i) {
            if (i > 0 && sigs[i].first != sigs[i-1].first) new_c++;
            new_classes[sigs[i].second] = new_c;
        }
        
        for (int i = 0; i < num_states; ++i) {
            if (ec_class[i] != new_classes[i]) {
                ec_class[i] = new_classes[i];
                changed = true;
            }
        }
    }
}

// Filter possible candidates based on observed wall distance
vector<int> filter_states(const vector<int>& current_s, int d) {
    vector<int> next_s;
    next_s.reserve(current_s.size());
    for (int id : current_s) {
        if (wall_dist[id] == d) {
            next_s.push_back(id);
        }
    }
    return next_s;
}

// Calculate heuristic score for an action: sum of squares of resulting group sizes
// Lower score means better split (more entropy)
long long score_split(const vector<int>& subset, int action) {
    map<int, int> counts;
    for (int id : subset) {
        int nid = next_state[id][action];
        if (nid == -1) return -1;
        counts[wall_dist[nid]]++;
    }
    long long score = 0;
    for (auto const& [val, count] : counts) {
        score += (long long)count * count;
    }
    return score;
}

// Check if an action results in diverse observations for the current set
bool causes_split(const vector<int>& subset, int action) {
    if (subset.empty()) return false;
    int first_obs = -1;
    bool set_flag = false;
    for (int id : subset) {
        int nid = next_state[id][action];
        if (nid == -1) return false;
        int obs = wall_dist[nid];
        if (!set_flag) {
            first_obs = obs;
            set_flag = true;
        } else {
            if (obs != first_obs) return true;
        }
    }
    return false;
}

// Apply move to all candidates in the subset
vector<int> apply_move(const vector<int>& subset, int action) {
    vector<int> res;
    res.reserve(subset.size());
    for (int id : subset) {
        res.push_back(next_state[id][action]);
    }
    sort(res.begin(), res.end());
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> R >> C)) return 0;
    grid.resize(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    init();
    compute_equivalence();

    // Initial set of candidates: all valid states
    vector<int> current_s;
    current_s.reserve(states.size());
    for (int i = 0; i < states.size(); ++i) current_s.push_back(i);

    while (true) {
        int d;
        cin >> d;
        if (d == -1) break;

        // Update candidates based on observation
        current_s = filter_states(current_s, d);

        if (current_s.empty()) return 0; // Should not happen

        // Check if all candidates are at the same position
        int r0 = states[current_s[0]].r;
        int c0 = states[current_s[0]].c;
        bool same_pos = true;
        for (size_t i = 1; i < current_s.size(); ++i) {
            if (states[current_s[i]].r != r0 || states[current_s[i]].c != c0) {
                same_pos = false;
                break;
            }
        }

        if (same_pos) {
            cout << "yes " << r0 + 1 << " " << c0 + 1 << endl;
            break;
        }

        // Check if remaining candidates are indistinguishable
        bool impossible = false;
        for (size_t i = 0; i < current_s.size(); ++i) {
            for (size_t j = i + 1; j < current_s.size(); ++j) {
                int u = current_s[i];
                int v = current_s[j];
                // Different positions but same equivalence class -> impossible to distinguish
                if ((states[u].r != states[v].r || states[u].c != states[v].c) && ec_class[u] == ec_class[v]) {
                    impossible = true;
                    break;
                }
            }
            if (impossible) break;
        }
        if (impossible) {
            cout << "no" << endl;
            break;
        }

        // Determine possible moves
        vector<int> actions = {0, 1}; // Left, Right
        if (d > 0) actions.push_back(2); // Step

        int best_action = -1;
        long long best_score = -1;
        long long current_sq = (long long)current_s.size() * current_s.size();

        // Evaluate immediate moves
        for (int a : actions) {
            long long sc = score_split(current_s, a);
            if (sc != -1) {
                if (best_score == -1 || sc < best_score) {
                    best_score = sc;
                    best_action = a;
                }
            }
        }

        // If no immediate move reduces the candidate set size (i.e., all yield score == current_sq),
        // perform BFS to find a sequence of moves that eventually splits the set.
        if (best_score != -1 && best_score < current_sq) {
            // Found a good immediate move
        } else {
            // BFS state: sorted vector of candidate IDs
            map<vector<int>, int> visited;
            vector<pair<vector<int>, int>> q;
            q.reserve(1000);
            
            q.push_back({current_s, -1});
            visited[current_s] = -1;
            
            int found_move = -1;
            int head = 0;
            int limit = 10000; // Limit search to avoid TLE

            while(head < q.size() && head < limit) {
                const vector<int>& s = q[head].first;
                int first_m = q[head].second;
                head++;
                
                // Determine valid actions for this set (all have same wall_dist)
                int dist = wall_dist[s[0]];
                vector<int> acts = {0, 1};
                if (dist > 0) acts.push_back(2);
                
                bool split_found = false;
                for (int a : acts) {
                    if (causes_split(s, a)) {
                        found_move = (first_m == -1 ? a : first_m);
                        split_found = true;
                        break;
                    }
                }
                
                if (split_found) break;
                
                // No split, generate next states
                for (int a : acts) {
                    vector<int> next_s_bfs = apply_move(s, a);
                    if (visited.find(next_s_bfs) == visited.end()) {
                        int fm = (first_m == -1 ? a : first_m);
                        visited[next_s_bfs] = fm;
                        q.push_back({next_s_bfs, fm});
                    }
                }
            }
            
            if (found_move != -1) best_action = found_move;
            else best_action = 0; // Should not reach here if not impossible
        }

        if (best_action == 0) cout << "left" << endl;
        else if (best_action == 1) cout << "right" << endl;
        else cout << "step" << endl;

        // Update belief state to reflect the move (before next observation)
        current_s = apply_move(current_s, best_action);
    }

    return 0;
}