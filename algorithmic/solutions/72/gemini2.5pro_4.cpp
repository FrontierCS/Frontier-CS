#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <set>
#include <algorithm>
#include <chrono>
#include <unordered_map>

using namespace std;

struct Vehicle {
    int id;
    int r_fixed, c_fixed;
    int len;
    bool is_horz;
};

vector<Vehicle> vehicles;
int vehicle_count;
int red_car_idx = -1;

using State = vector<int>;

struct StateHash {
    size_t operator()(const State& s) const {
        size_t seed = s.size();
        for(int x : s) {
            seed ^= x + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
        return seed;
    }
};

void state_to_board(const State& s, int board[6][6]) {
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            board[i][j] = 0;
        }
    }
    for (int i = 0; i < vehicle_count; ++i) {
        if (vehicles[i].is_horz) {
            int r = vehicles[i].r_fixed;
            int c = s[i];
            for (int k = 0; k < vehicles[i].len; ++k) {
                if (r >=0 && r < 6 && c + k >= 0 && c + k < 6)
                    board[r][c + k] = vehicles[i].id;
            }
        } else {
            int r = s[i];
            int c = vehicles[i].c_fixed;
            for (int k = 0; k < vehicles[i].len; ++k) {
                if (r + k >= 0 && r + k < 6 && c >= 0 && c < 6)
                    board[r + k][c] = vehicles[i].id;
            }
        }
    }
}

int heuristic(const State& s) {
    int red_car_c = s[red_car_idx];
    if (red_car_c >= 6) return 0;
    
    set<int> blockers;
    int board[6][6];
    state_to_board(s, board);
    
    for (int c = red_car_c + vehicles[red_car_idx].len; c < 6; ++c) {
        if (board[2][c] != 0) {
            blockers.insert(board[2][c]);
        }
    }
    return blockers.size() + (6 - red_car_c);
}

int solve_with_a_star(const State& start_state) {
    if (start_state[red_car_idx] >= 6) {
        return 0;
    }

    priority_queue<pair<int, State>, vector<pair<int, State>>, greater<pair<int, State>>> pq;
    unordered_map<State, int, StateHash> g_score;

    g_score[start_state] = 0;
    pq.push({heuristic(start_state), start_state});

    while (!pq.empty()) {
        State u = pq.top().second;
        pq.pop();

        if (u[red_car_idx] >= 6) {
            return g_score[u];
        }
        if (g_score[u] > 50) continue; 

        int current_g = g_score[u];
        int board[6][6];
        state_to_board(u, board);

        for (int i = 0; i < vehicle_count; ++i) {
            if (vehicles[i].is_horz) {
                int r = vehicles[i].r_fixed;
                int c = u[i];
                int max_c = (i == red_car_idx) ? 6 : 6 - vehicles[i].len;
                if (c < max_c && (c + vehicles[i].len >= 6 || board[r][c + vehicles[i].len] == 0)) {
                    State v = u; v[i]++;
                    if (g_score.find(v) == g_score.end() || current_g + 1 < g_score[v]) {
                        g_score[v] = current_g + 1;
                        pq.push({g_score[v] + heuristic(v), v});
                    }
                }
                if (c > 0 && board[r][c - 1] == 0) {
                    State v = u; v[i]--;
                    if (g_score.find(v) == g_score.end() || current_g + 1 < g_score[v]) {
                        g_score[v] = current_g + 1;
                        pq.push({g_score[v] + heuristic(v), v});
                    }
                }
            } else {
                int r = u[i];
                int c = vehicles[i].c_fixed;
                if (r + vehicles[i].len < 6 && board[r + vehicles[i].len][c] == 0) {
                    State v = u; v[i]++;
                    if (g_score.find(v) == g_score.end() || current_g + 1 < g_score[v]) {
                        g_score[v] = current_g + 1;
                        pq.push({g_score[v] + heuristic(v), v});
                    }
                }
                if (r > 0 && board[r - 1][c] == 0) {
                    State v = u; v[i]--;
                    if (g_score.find(v) == g_score.end() || current_g + 1 < g_score[v]) {
                        g_score[v] = current_g + 1;
                        pq.push({g_score[v] + heuristic(v), v});
                    }
                }
            }
        }
    }
    return -1; 
}


struct Move {
    int vehicle_id;
    char dir;
};

void parse_input(int initial_board[6][6], State& initial_state) {
    map<int, vector<pair<int, int>>> vehicle_coords;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (initial_board[r][c] != 0) {
                vehicle_coords[initial_board[r][c]].push_back({r, c});
            }
        }
    }

    vehicle_count = vehicle_coords.size();
    vehicles.resize(vehicle_count);
    initial_state.resize(vehicle_count);
    map<int, int> id_to_idx;
    int idx_counter = 0;

    vector<int> sorted_ids;
    for(auto const& [id, coords] : vehicle_coords) sorted_ids.push_back(id);
    sort(sorted_ids.begin(), sorted_ids.end());

    for(int id : sorted_ids) id_to_idx[id] = idx_counter++;

    for (auto const& [id, coords_pair] : vehicle_coords) {
        auto coords = coords_pair;
        sort(coords.begin(), coords.end());

        int current_idx = id_to_idx[id];
        int r_min = coords[0].first;
        int c_min = coords[0].second;

        vehicles[current_idx].id = id;
        vehicles[current_idx].len = coords.size();
        
        if (coords.size() > 1 && coords[0].first == coords[1].first) {
            vehicles[current_idx].is_horz = true;
            vehicles[current_idx].r_fixed = r_min;
            initial_state[current_idx] = c_min;
        } else {
            vehicles[current_idx].is_horz = false;
            vehicles[current_idx].c_fixed = c_min;
            initial_state[current_idx] = r_min;
        }

        if (id == 1) red_car_idx = current_idx;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int initial_board[6][6];
    for (int i = 0; i < 6; ++i) for (int j = 0; j < 6; ++j) cin >> initial_board[i][j];

    State initial_state;
    parse_input(initial_board, initial_state);

    queue<pair<State, vector<Move>>> q;
    unordered_map<State, bool, StateHash> visited;

    q.push({initial_state, {}});
    visited[initial_state] = true;

    int max_dist = solve_with_a_star(initial_state);
    vector<Move> best_moves;

    auto start_time = chrono::high_resolution_clock::now();

    while (!q.empty()) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration<double>(now - start_time).count() > 1.95) break;

        pair<State, vector<Move>> curr = q.front();
        q.pop();

        State u = curr.first;
        vector<Move> moves_to_u = curr.second;

        int board[6][6];
        state_to_board(u, board);

        for (int i = 0; i < vehicle_count; ++i) {
            if (vehicles[i].is_horz) {
                int r = vehicles[i].r_fixed;
                int c = u[i];
                int max_c = (i == red_car_idx) ? 6 : 6 - vehicles[i].len;
                if (c < max_c && (c + vehicles[i].len >= 6 || board[r][c + vehicles[i].len] == 0)) {
                    State v = u; v[i]++;
                    if (visited.find(v) == visited.end()) {
                        visited[v] = true;
                        int d = solve_with_a_star(v);
                        if (d != -1) {
                            vector<Move> moves_to_v = moves_to_u;
                            moves_to_v.push_back({vehicles[i].id, 'R'});
                            if (d > max_dist) { max_dist = d; best_moves = moves_to_v; }
                            q.push({v, moves_to_v});
                        }
                    }
                }
                if (c > 0 && board[r][c - 1] == 0) {
                    State v = u; v[i]--;
                    if (visited.find(v) == visited.end()) {
                        visited[v] = true;
                        int d = solve_with_a_star(v);
                        if (d != -1) {
                            vector<Move> moves_to_v = moves_to_u;
                            moves_to_v.push_back({vehicles[i].id, 'L'});
                            if (d > max_dist) { max_dist = d; best_moves = moves_to_v; }
                            q.push({v, moves_to_v});
                        }
                    }
                }
            } else {
                int r = u[i];
                int c = vehicles[i].c_fixed;
                if (r + vehicles[i].len < 6 && board[r + vehicles[i].len][c] == 0) {
                    State v = u; v[i]++;
                    if (visited.find(v) == visited.end()) {
                        visited[v] = true;
                        int d = solve_with_a_star(v);
                        if (d != -1) {
                            vector<Move> moves_to_v = moves_to_u;
                            moves_to_v.push_back({vehicles[i].id, 'D'});
                            if (d > max_dist) { max_dist = d; best_moves = moves_to_v; }
                            q.push({v, moves_to_v});
                        }
                    }
                }
                if (r > 0 && board[r - 1][c] == 0) {
                    State v = u; v[i]--;
                    if (visited.find(v) == visited.end()) {
                        visited[v] = true;
                        int d = solve_with_a_star(v);
                        if (d != -1) {
                            vector<Move> moves_to_v = moves_to_u;
                            moves_to_v.push_back({vehicles[i].id, 'U'});
                            if (d > max_dist) { max_dist = d; best_moves = moves_to_v; }
                            q.push({v, moves_to_v});
                        }
                    }
                }
            }
        }
    }

    cout << max_dist << " " << best_moves.size() << endl;
    for (const auto& move : best_moves) {
        cout << move.vehicle_id << " " << move.dir << endl;
    }

    return 0;
}