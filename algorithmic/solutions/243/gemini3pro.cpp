#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <queue>
#include <map>
#include <cstring>

using namespace std;

// Problem constants
int R, C;
vector<string> grid_map;

// Directions: 0: N, 1: E, 2: S, 3: W
int dr[] = {-1, 0, 1, 0};
int dc[] = {0, 1, 0, -1};
string action_str[] = {"left", "right", "step"};

struct State {
    int r, c, dir;
};

// Precomputed distances to walls
int wall_dists[105][105][4];

void precompute_dists() {
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid_map[r][c] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                int dist = 0;
                int nr = r + dr[d];
                int nc = c + dc[d];
                while (nr >= 0 && nr < R && nc >= 0 && nc < C && grid_map[nr][nc] == '.') {
                    dist++;
                    nr += dr[d];
                    nc += dc[d];
                }
                wall_dists[r][c][d] = dist;
            }
        }
    }
}

State apply_action(State s, int action) {
    if (action == 0) s.dir = (s.dir + 3) % 4; // Left
    else if (action == 1) s.dir = (s.dir + 1) % 4; // Right
    else { s.r += dr[s.dir]; s.c += dc[s.dir]; } // Step
    return s;
}

int get_obs(State s) {
    return wall_dists[s.r][s.c][s.dir];
}

// Visited array for BFS
bool visited[105][105][4];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> R >> C)) return 0;
    grid_map.resize(R);
    for (int i = 0; i < R; ++i) cin >> grid_map[i];

    precompute_dists();

    // Initialize candidates with all open squares and all directions
    vector<State> candidates;
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid_map[r][c] == '.') {
                for (int d = 0; d < 4; ++d) candidates.push_back({r, c, d});
            }
        }
    }

    while (true) {
        int D;
        cin >> D;
        if (D == -1) break;

        // Filter candidates based on observation D
        vector<State> next_candidates;
        next_candidates.reserve(candidates.size());
        for (const auto& s : candidates) {
            if (get_obs(s) == D) next_candidates.push_back(s);
        }
        candidates = next_candidates;

        if (candidates.empty()) {
            cout << "no" << endl;
            return 0;
        }

        // Check if unique position is determined
        int solved_r = candidates[0].r;
        int solved_c = candidates[0].c;
        bool solved = true;
        for (size_t i = 1; i < candidates.size(); ++i) {
            if (candidates[i].r != solved_r || candidates[i].c != solved_c) {
                solved = false;
                break;
            }
        }

        if (solved) {
            cout << "yes " << solved_r + 1 << " " << solved_c + 1 << endl;
            return 0;
        }

        // Determine best action
        // Valid immediate actions
        vector<int> possible_actions;
        possible_actions.push_back(0); // Left
        possible_actions.push_back(1); // Right
        if (D > 0) possible_actions.push_back(2); // Step

        int best_action = -1;
        long long min_score = -1;
        bool split_found = false;

        // Greedy strategy: 1-step lookahead to minimize entropy (maximize split)
        for (int a : possible_actions) {
            map<int, int> counts;
            int first_obs = -1;
            bool all_same = true;
            for (size_t i = 0; i < candidates.size(); ++i) {
                State ns = apply_action(candidates[i], a);
                int o = get_obs(ns);
                counts[o]++;
                if (i == 0) first_obs = o;
                else if (o != first_obs) all_same = false;
            }

            if (!all_same) {
                long long score = 0;
                for (auto const& [val, count] : counts) score += (long long)count * count;
                
                if (!split_found || score < min_score) {
                    min_score = score;
                    best_action = a;
                    split_found = true;
                }
            }
        }

        if (split_found) {
            cout << action_str[best_action] << endl;
        } else {
            // If no immediate split possible, use BFS to find a sequence that splits
            memset(visited, 0, sizeof(visited));
            queue<pair<vector<State>, int>> q;
            q.push({candidates, -1});
            visited[candidates[0].r][candidates[0].c][candidates[0].dir] = true;
            int found_action = -1;

            while (!q.empty()) {
                auto curr = q.front();
                q.pop();
                vector<State>& curr_S = curr.first;
                int first_act = curr.second;

                for (int a = 0; a < 3; ++a) {
                    // Check if action 'a' is valid for all candidates in current set
                    bool possible = true;
                    if (a == 2) { // Step
                        for (const auto& s : curr_S) {
                            if (wall_dists[s.r][s.c][s.dir] == 0) {
                                possible = false;
                                break;
                            }
                        }
                    }
                    if (!possible) continue;

                    vector<State> next_S;
                    next_S.reserve(curr_S.size());
                    int obs0 = -1;
                    bool split = false;
                    for (size_t i = 0; i < curr_S.size(); ++i) {
                        State ns = apply_action(curr_S[i], a);
                        next_S.push_back(ns);
                        int o = get_obs(ns);
                        if (i == 0) obs0 = o;
                        else if (o != obs0) split = true;
                    }

                    if (split) {
                        found_action = (first_act == -1) ? a : first_act;
                        goto bfs_end;
                    } else {
                        State& rep = next_S[0];
                        if (!visited[rep.r][rep.c][rep.dir]) {
                            visited[rep.r][rep.c][rep.dir] = true;
                            q.push({next_S, (first_act == -1) ? a : first_act});
                        }
                    }
                }
            }
            bfs_end:;
            if (found_action != -1) cout << action_str[found_action] << endl;
            else {
                // If BFS exhausts reachable states without splitting, it's impossible
                cout << "no" << endl;
                return 0;
            }
        }
    }
    return 0;
}