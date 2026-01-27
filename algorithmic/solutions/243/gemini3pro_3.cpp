#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <queue>
#include <tuple>
#include <cmath>

using namespace std;

// State representation: row, column, direction
// Direction: 0=North, 1=East, 2=South, 3=West
struct State {
    int r, c, dir;
    bool operator<(const State& other) const {
        return tie(r, c, dir) < tie(other.r, other.c, other.dir);
    }
    bool operator==(const State& other) const {
        return tie(r, c, dir) == tie(other.r, other.c, other.dir);
    }
    bool operator!=(const State& other) const {
        return !(*this == other);
    }
};

int R, C;
vector<string> grid;
int dr[] = {-1, 0, 1, 0}; // N, E, S, W
int dc[] = {0, 1, 0, -1};

// Precomputed distances: wall_dist[r][c][dir]
int wall_dist[105][105][4];
// Equivalence classes for detecting impossible cases and guiding BFS
int equiv_class[105][105][4];

// Global candidates
vector<State> candidates;
vector<int> plan;
string action_str[] = {"left", "right", "step"};

bool is_valid(int r, int c) {
    return r >= 0 && r < R && c >= 0 && c < C && grid[r][c] == '.';
}

void compute_wall_dists() {
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                int dist = 0;
                int cr = r, cc = c;
                while (true) {
                    int nr = cr + dr[d];
                    int nc = cc + dc[d];
                    if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc] == '#') {
                        break;
                    }
                    cr = nr;
                    cc = nc;
                    dist++;
                }
                wall_dist[r][c][d] = dist;
            }
        }
    }
}

void compute_equiv_classes() {
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                equiv_class[r][c][d] = wall_dist[r][c][d];
            }
        }
    }

    while (true) {
        map<vector<int>, int> next_classes_map;
        int next_id = 0;
        int new_equiv[105][105][4];
        
        // Build new signatures
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (grid[r][c] == '#') continue;
                for (int d = 0; d < 4; ++d) {
                    vector<int> signature;
                    signature.push_back(equiv_class[r][c][d]);
                    signature.push_back(equiv_class[r][c][(d + 3) % 4]); // Left
                    signature.push_back(equiv_class[r][c][(d + 1) % 4]); // Right
                    if (wall_dist[r][c][d] > 0) {
                        signature.push_back(equiv_class[r + dr[d]][c + dc[d]][d]); // Step
                    } else {
                        signature.push_back(-1);
                    }

                    if (next_classes_map.find(signature) == next_classes_map.end()) {
                        next_classes_map[signature] = next_id++;
                    }
                    new_equiv[r][c][d] = next_classes_map[signature];
                }
            }
        }

        // Check convergence
        int old_max = -1;
        for(int r=0;r<R;++r) for(int c=0;c<C;++c) for(int d=0;d<4;++d) 
            if(grid[r][c]=='.') old_max = max(old_max, equiv_class[r][c][d]);

        if (next_id == old_max + 1) break;

        for(int r=0;r<R;++r) for(int c=0;c<C;++c) for(int d=0;d<4;++d) 
            if(grid[r][c]=='.') equiv_class[r][c][d] = new_equiv[r][c][d];
    }
}

State apply_move(State s, int action) {
    if (action == 0) return {s.r, s.c, (s.dir + 3) % 4};
    if (action == 1) return {s.r, s.c, (s.dir + 1) % 4};
    if (action == 2) return {s.r + dr[s.dir], s.c + dc[s.dir], s.dir};
    return s;
}

int get_obs(State s) {
    return wall_dist[s.r][s.c][s.dir];
}

void solve_bfs(State u, State v) {
    using BFSState = pair<State, State>;
    queue<pair<BFSState, int>> q;
    map<BFSState, int> visited_first_move; // Stores the first move taken to reach this state
    
    BFSState start = {u, v};
    q.push({start, 0});

    map<BFSState, int> dist_map;
    dist_map[start] = 0;
    
    // map to store the first action taken on the path to a state
    map<BFSState, int> first_move_map;

    while(!q.empty()){
        auto [curr, d] = q.front();
        q.pop();

        State s1 = curr.first;
        State s2 = curr.second;

        // Check if distinguished
        if (get_obs(s1) != get_obs(s2)) {
            plan.clear();
            plan.push_back(first_move_map[curr]);
            return;
        }

        vector<int> actions = {0, 1};
        if (get_obs(s1) > 0) actions.push_back(2); // Step allowed

        for (int act : actions) {
            State n1 = apply_move(s1, act);
            State n2 = apply_move(s2, act);
            BFSState next = {n1, n2};

            if (dist_map.find(next) == dist_map.end()) {
                dist_map[next] = d + 1;
                if (d == 0) first_move_map[next] = act;
                else first_move_map[next] = first_move_map[curr];
                q.push({next, d + 1});
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> R >> C)) return 0;
    grid.resize(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    compute_wall_dists();
    compute_equiv_classes();

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
        int d_obs;
        cin >> d_obs;
        if (d_obs == -1) break;

        vector<State> next_candidates;
        for (const auto& s : candidates) {
            if (get_obs(s) == d_obs) {
                next_candidates.push_back(s);
            }
        }
        candidates = next_candidates;

        if (candidates.empty()) break; 

        int ur = candidates[0].r, uc = candidates[0].c;
        bool unique_pos = true;
        for (size_t i = 1; i < candidates.size(); ++i) {
            if (candidates[i].r != ur || candidates[i].c != uc) {
                unique_pos = false;
                break;
            }
        }

        if (unique_pos) {
            cout << "yes " << ur + 1 << " " << uc + 1 << endl;
            break;
        }

        int first_ec = equiv_class[candidates[0].r][candidates[0].c][candidates[0].dir];
        bool all_same_ec = true;
        for (const auto& s : candidates) {
            if (equiv_class[s.r][s.c][s.dir] != first_ec) {
                all_same_ec = false;
                break;
            }
        }
        if (all_same_ec) {
            cout << "no" << endl;
            break;
        }

        // Greedy Strategy
        double best_score = 1e18;
        vector<int> best_actions;
        
        vector<int> possible_actions = {0, 1};
        if (d_obs > 0) possible_actions.push_back(2);

        for (int act : possible_actions) {
            map<int, int> obs_counts;
            for (const auto& s : candidates) {
                State ns = apply_move(s, act);
                obs_counts[get_obs(ns)]++;
            }
            double score = 0;
            for (auto const& [val, count] : obs_counts) {
                score += (double)count * count;
            }
            if (score < best_score - 0.1) {
                best_score = score;
                best_actions.clear();
                best_actions.push_back(act);
            } else if (abs(score - best_score) < 0.1) {
                best_actions.push_back(act);
            }
        }

        int chosen_action = -1;
        double current_sq = (double)candidates.size() * candidates.size();

        // If any action reduces expected candidates (score < |S|^2)
        if (best_score < current_sq - 0.5) {
            // Heuristic tie-breaking
            bool has_step = false, has_left = false, has_right = false;
            for(int a : best_actions) {
                if(a==2) has_step=true;
                if(a==0) has_left=true;
                if(a==1) has_right=true;
            }
            if(has_step) chosen_action = 2;
            else if(has_left) chosen_action = 0;
            else chosen_action = 1;
        } else {
            // BFS needed to break ties / find separating sequence
            State u = candidates[0];
            State v = candidates[0];
            for (const auto& s : candidates) {
                if (equiv_class[s.r][s.c][s.dir] != equiv_class[u.r][u.c][u.dir]) {
                    v = s;
                    break;
                }
            }
            solve_bfs(u, v);
            if (!plan.empty()) chosen_action = plan[0];
            else chosen_action = best_actions[0]; // Fallback
        }

        cout << action_str[chosen_action] << endl;
    }
    return 0;
}