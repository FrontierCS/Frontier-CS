#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <tuple>
#include <map>
#include <set>
#include <cmath>

using namespace std;

// Global variables for map dimensions and data
int R, C;
vector<string> grid;

// Direction vectors: North, East, South, West
// N: (-1, 0), E: (0, 1), S: (1, 0), W: (0, -1)
int dr[] = {-1, 0, 1, 0}; 
int dc[] = {0, 1, 0, -1};

// State representation
struct State {
    int r, c, dir;
    bool operator<(const State& o) const {
        return tie(r, c, dir) < tie(o.r, o.c, o.dir);
    }
    bool operator==(const State& o) const {
        return tie(r, c, dir) == tie(o.r, o.c, o.dir);
    }
};

// Precomputed data
int dist_map[105][105][4]; // Distance to wall for each cell and direction
int class_id[105][105][4]; // Equivalence class ID for each state

// Helper to compute distance to wall
int get_wall_dist(int r, int c, int dir) {
    int d = 0;
    while (true) {
        int nr = r + dr[dir] * (d + 1);
        int nc = c + dc[dir] * (d + 1);
        if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc] == '#') return d;
        d++;
    }
}

// Precompute distances and equivalence classes
void precompute() {
    // 1. Compute distances
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '.') {
                for (int d = 0; d < 4; ++d) {
                    dist_map[r][c][d] = get_wall_dist(r, c, d);
                }
            }
        }
    }

    // 2. Initialize equivalence classes based on immediate observation (distance)
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            for (int d = 0; d < 4; ++d) {
                if (grid[r][c] == '.') {
                    class_id[r][c][d] = dist_map[r][c][d];
                } else {
                    class_id[r][c][d] = -1;
                }
            }
        }
    }

    // 3. Iteratively refine classes
    // Two states are equivalent if they have same observation and transition to equivalent states for all actions.
    while (true) {
        vector<pair<vector<int>, int>> mapping;
        mapping.reserve(R * C * 4);
        
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (grid[r][c] != '.') continue;
                for (int d = 0; d < 4; ++d) {
                    vector<int> sig;
                    sig.push_back(class_id[r][c][d]); // Current observation
                    sig.push_back(class_id[r][c][(d + 3) % 4]); // Result of Left
                    sig.push_back(class_id[r][c][(d + 1) % 4]); // Result of Right
                    
                    if (dist_map[r][c][d] > 0) {
                        sig.push_back(class_id[r + dr[d]][c + dc[d]][d]); // Result of Step
                    } else {
                        sig.push_back(-2); // Step invalid (blocked)
                    }
                    
                    // Store index to map back: (r, c, d) flattened
                    mapping.push_back({sig, (r * C + c) * 4 + d});
                }
            }
        }
        
        sort(mapping.begin(), mapping.end());
        
        // Assign new IDs based on sorted signatures
        vector<int> new_ids(R * C * 4);
        int current_id = 0;
        
        for(size_t i = 0; i < mapping.size(); ++i) {
            if(i > 0 && mapping[i].first != mapping[i-1].first) current_id++;
            new_ids[mapping[i].second] = current_id;
        }
        
        // Check convergence (number of classes stops increasing)
        static int prev_class_count = -1;
        if (current_id == prev_class_count) break;
        prev_class_count = current_id;

        // Update class_id table
        for(size_t i = 0; i < mapping.size(); ++i) {
            int idx = mapping[i].second;
            int r = idx / 4 / C;
            int c = (idx / 4) % C;
            int d = idx % 4;
            class_id[r][c][d] = new_ids[idx];
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> R >> C)) return 0;
    grid.resize(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    precompute();

    // Initial set of candidate states: all directions at all open squares
    vector<State> candidates;
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '.') {
                for (int d = 0; d < 4; ++d) {
                    candidates.push_back({r, c, d});
                }
            }
        }
    }

    while (true) {
        int obs;
        cin >> obs;
        if (obs == -1) break;

        // Filter candidates based on observation
        vector<State> next_candidates;
        next_candidates.reserve(candidates.size());
        for (const auto& s : candidates) {
            if (dist_map[s.r][s.c][s.dir] == obs) {
                next_candidates.push_back(s);
            }
        }
        candidates = next_candidates;

        // Check if position is uniquely determined
        if (candidates.empty()) return 0; // Should not happen given valid inputs

        int first_r = candidates[0].r;
        int first_c = candidates[0].c;
        bool same_pos = true;
        for (const auto& s : candidates) {
            if (s.r != first_r || s.c != first_c) {
                same_pos = false;
                break;
            }
        }

        if (same_pos) {
            cout << "yes " << first_r + 1 << " " << first_c + 1 << endl;
            return 0;
        }

        // Check for impossibility
        // If there are two candidates with different positions but same equivalence class, 
        // we can never distinguish them reliably.
        map<int, pair<int, int>> cls_to_pos;
        bool impossible = false;
        for (const auto& s : candidates) {
            int cls = class_id[s.r][s.c][s.dir];
            if (cls_to_pos.count(cls)) {
                if (cls_to_pos[cls] != make_pair(s.r, s.c)) {
                    impossible = true;
                    break;
                }
            } else {
                cls_to_pos[cls] = {s.r, s.c};
            }
        }

        if (impossible) {
            cout << "no" << endl;
            return 0;
        }

        // Decide next action using greedy strategy
        // Actions: 0: Left, 1: Right, 2: Step (only valid if obs > 0)
        vector<string> action_names = {"left", "right", "step"};
        vector<int> actions;
        actions.push_back(0);
        actions.push_back(1);
        if (obs > 0) actions.push_back(2);

        double best_score_max = 1e9;
        long long best_score_sq = -1; // Higher is worse
        int best_action = -1;

        // Evaluate each action
        for (int act : actions) {
            map<int, int> counts;
            // Simulate action for all candidates and count distribution of next observations
            for (const auto& s : candidates) {
                State next_s = s;
                if (act == 0) next_s.dir = (s.dir + 3) % 4;
                else if (act == 1) next_s.dir = (s.dir + 1) % 4;
                else if (act == 2) {
                    next_s.r += dr[s.dir];
                    next_s.c += dc[s.dir];
                }
                
                // Get observation in the new state
                int next_obs = dist_map[next_s.r][next_s.c][next_s.dir];
                counts[next_obs]++;
            }

            // Calculate score metrics
            int current_max = 0;
            long long current_sq = 0;
            for (auto const& [val, count] : counts) {
                if (count > current_max) current_max = count;
                current_sq += (long long)count * count;
            }

            // Greedy criteria: 
            // 1. Minimize Max subset size (Minimax)
            // 2. Minimize Sum of squares of sizes (Entropy approximation)
            // 3. Prefer Step over Turns
            bool better = false;
            if (best_action == -1) better = true;
            else {
                if (current_max < best_score_max) better = true;
                else if (current_max == best_score_max) {
                    if (best_score_sq == -1 || current_sq < best_score_sq) better = true;
                    else if (current_sq == best_score_sq) {
                        // Tie-breaker: Prefer Step (2) > Left (0) > Right (1)
                        // Priority values: Step=3, Left=2, Right=1
                        int p_curr = (act == 2 ? 3 : (act == 0 ? 2 : 1));
                        int p_best = (best_action == 2 ? 3 : (best_action == 0 ? 2 : 1));
                        if (p_curr > p_best) better = true;
                    }
                }
            }

            if (better) {
                best_score_max = current_max;
                best_score_sq = current_sq;
                best_action = act;
            }
        }

        cout << action_names[best_action] << endl;

        // Update local candidates to reflect the chosen action
        vector<State> next_states;
        next_states.reserve(candidates.size());
        for (const auto& s : candidates) {
            State next_s = s;
            if (best_action == 0) next_s.dir = (s.dir + 3) % 4;
            else if (best_action == 1) next_s.dir = (s.dir + 1) % 4;
            else {
                next_s.r += dr[s.dir];
                next_s.c += dc[s.dir];
            }
            next_states.push_back(next_s);
        }
        candidates = next_states;
    }

    return 0;
}