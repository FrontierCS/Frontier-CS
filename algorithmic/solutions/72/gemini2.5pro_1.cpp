#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <algorithm>
#include <unordered_map>

using namespace std;

struct VInfo {
    int id;
    int len;
    bool is_horizontal;
    int fixed_coord;
};

struct Move {
    int id;
    char dir;
};

vector<VInfo> v_infos;
map<int, int> id_to_idx;
int red_car_idx;
int num_vehicles;

long long state_to_ll(const vector<int>& s) {
    long long res = 0;
    for (int x : s) {
        res = (res << 3) | x;
    }
    return res;
}

vector<int> ll_to_state(long long ll) {
    vector<int> s(num_vehicles);
    for (int i = num_vehicles - 1; i >= 0; --i) {
        s[i] = ll & 7;
        ll >>= 3;
    }
    return s;
}

int bfs_solve(const vector<int>& start_state) {
    long long start_ll = state_to_ll(start_state);
    queue<pair<long long, int>> q;
    q.push({start_ll, 0});
    unordered_map<long long, int> dist;
    dist[start_ll] = 0;

    while (!q.empty()) {
        auto [curr_ll, d] = q.front();
        q.pop();

        vector<int> curr_state = ll_to_state(curr_ll);

        if (curr_state[red_car_idx] == 6) {
            return d;
        }

        bool occupied[6][6] = {};
        for (int i = 0; i < num_vehicles; ++i) {
            if (v_infos[i].is_horizontal) {
                int r = v_infos[i].fixed_coord;
                for (int k = 0; k < v_infos[i].len; ++k) {
                    int c = curr_state[i] + k;
                    if (c >= 0 && c < 6) {
                        occupied[r][c] = true;
                    }
                }
            } else {
                int c = v_infos[i].fixed_coord;
                for (int k = 0; k < v_infos[i].len; ++k) {
                    int r = curr_state[i] + k;
                    if (r >= 0 && r < 6) {
                        occupied[r][c] = true;
                    }
                }
            }
        }

        for (int i = 0; i < num_vehicles; ++i) {
            if (v_infos[i].is_horizontal) {
                int r = v_infos[i].fixed_coord;
                int c = curr_state[i];
                int len = v_infos[i].len;

                // Move right
                if (c < 6) {
                    int front_c = c + len;
                    bool can_move = false;
                    if (front_c < 6) {
                        if (!occupied[r][front_c]) can_move = true;
                    } else { // front_c >= 6
                        if (v_infos[i].id == 1 && r == 2) can_move = true;
                    }
                    if (can_move) {
                        vector<int> next_state = curr_state;
                        next_state[i]++;
                        long long next_ll = state_to_ll(next_state);
                        if (dist.find(next_ll) == dist.end()) {
                            dist[next_ll] = d + 1;
                            q.push({next_ll, d + 1});
                        }
                    }
                }

                // Move left
                if (c > 0) {
                    int back_c = c - 1;
                    if (back_c >= 0 && !occupied[r][back_c]) {
                        vector<int> next_state = curr_state;
                        next_state[i]--;
                        long long next_ll = state_to_ll(next_state);
                        if (dist.find(next_ll) == dist.end()) {
                            dist[next_ll] = d + 1;
                            q.push({next_ll, d + 1});
                        }
                    }
                }
            } else { // Vertical
                int r = curr_state[i];
                int c = v_infos[i].fixed_coord;
                int len = v_infos[i].len;

                // Move down
                if (r + len < 6 && !occupied[r + len][c]) {
                    vector<int> next_state = curr_state;
                    next_state[i]++;
                    long long next_ll = state_to_ll(next_state);
                    if (dist.find(next_ll) == dist.end()) {
                        dist[next_ll] = d + 1;
                        q.push({next_ll, d + 1});
                    }
                }

                // Move up
                if (r > 0 && !occupied[r - 1][c]) {
                    vector<int> next_state = curr_state;
                    next_state[i]--;
                    long long next_ll = state_to_ll(next_state);
                    if (dist.find(next_ll) == dist.end()) {
                        dist[next_ll] = d + 1;
                        q.push({next_ll, d + 1});
                    }
                }
            }
        }
    }
    return -1; 
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    vector<vector<int>> board(6, vector<int>(6));
    map<int, vector<pair<int, int>>> cells;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> board[i][j];
            if (board[i][j] != 0) {
                cells[board[i][j]].push_back({i, j});
            }
        }
    }

    vector<int> ids;
    for (auto const& [id, _] : cells) {
        ids.push_back(id);
    }
    sort(ids.begin(), ids.end());

    num_vehicles = ids.size();
    v_infos.resize(num_vehicles);
    vector<int> initial_state(num_vehicles);

    for (int i = 0; i < num_vehicles; ++i) {
        int id = ids[i];
        id_to_idx[id] = i;
        v_infos[i].id = id;
        if (id == 1) {
            red_car_idx = i;
        }

        auto& vehicle_cells = cells[id];
        sort(vehicle_cells.begin(), vehicle_cells.end());
        
        v_infos[i].len = vehicle_cells.size();
        int r0 = vehicle_cells[0].first;
        int c0 = vehicle_cells[0].second;

        if (vehicle_cells.size() > 1 && vehicle_cells[0].first == vehicle_cells[1].first) {
            v_infos[i].is_horizontal = true;
            v_infos[i].fixed_coord = r0;
            initial_state[i] = c0;
        } else {
            v_infos[i].is_horizontal = false;
            v_infos[i].fixed_coord = c0;
            initial_state[i] = r0;
        }
    }

    long long initial_ll = state_to_ll(initial_state);
    queue<long long> q;
    q.push(initial_ll);
    unordered_map<long long, pair<long long, Move>> parent;
    parent[initial_ll] = {-1LL, {-1, ' '}};

    int max_solve_steps = -1;
    long long best_state_ll = -1LL;
    
    while (!q.empty()) {
        long long curr_ll = q.front();
        q.pop();

        vector<int> curr_state = ll_to_state(curr_ll);
        int solve_steps = bfs_solve(curr_state);

        if (solve_steps > max_solve_steps) {
            max_solve_steps = solve_steps;
            best_state_ll = curr_ll;
        }

        bool occupied[6][6] = {};
        for (int i = 0; i < num_vehicles; ++i) {
            if (v_infos[i].is_horizontal) {
                int r = v_infos[i].fixed_coord;
                for (int k = 0; k < v_infos[i].len; ++k) {
                    int c = curr_state[i] + k;
                    if (c >= 0 && c < 6) occupied[r][c] = true;
                }
            } else {
                int c = v_infos[i].fixed_coord;
                for (int k = 0; k < v_infos[i].len; ++k) {
                    int r = curr_state[i] + k;
                    if (r >= 0 && r < 6) occupied[r][c] = true;
                }
            }
        }

        for (int i = 0; i < num_vehicles; ++i) {
            if (v_infos[i].is_horizontal) {
                int r = v_infos[i].fixed_coord;
                int c = curr_state[i];
                int len = v_infos[i].len;
                
                if (c + len < 6 && !occupied[r][c + len]) {
                    vector<int> next_state = curr_state;
                    next_state[i]++;
                    long long next_ll = state_to_ll(next_state);
                    if (parent.find(next_ll) == parent.end()) {
                        parent[next_ll] = {curr_ll, {v_infos[i].id, 'R'}};
                        q.push(next_ll);
                    }
                }
                if (c > 0 && !occupied[r][c - 1]) {
                    vector<int> next_state = curr_state;
                    next_state[i]--;
                    long long next_ll = state_to_ll(next_state);
                    if (parent.find(next_ll) == parent.end()) {
                        parent[next_ll] = {curr_ll, {v_infos[i].id, 'L'}};
                        q.push(next_ll);
                    }
                }
            } else {
                int r = curr_state[i];
                int c = v_infos[i].fixed_coord;
                int len = v_infos[i].len;

                if (r + len < 6 && !occupied[r + len][c]) {
                    vector<int> next_state = curr_state;
                    next_state[i]++;
                    long long next_ll = state_to_ll(next_state);
                    if (parent.find(next_ll) == parent.end()) {
                        parent[next_ll] = {curr_ll, {v_infos[i].id, 'D'}};
                        q.push(next_ll);
                    }
                }
                if (r > 0 && !occupied[r - 1][c]) {
                    vector<int> next_state = curr_state;
                    next_state[i]--;
                    long long next_ll = state_to_ll(next_state);
                    if (parent.find(next_ll) == parent.end()) {
                        parent[next_ll] = {curr_ll, {v_infos[i].id, 'U'}};
                        q.push(next_ll);
                    }
                }
            }
        }
    }

    vector<Move> path;
    if (best_state_ll != -1LL) {
        long long s_ll = best_state_ll;
        while(s_ll != initial_ll){
            auto [p_ll, m] = parent[s_ll];
            path.push_back(m);
            s_ll = p_ll;
        }
        reverse(path.begin(), path.end());
    }

    cout << max_solve_steps << " " << path.size() << endl;
    for(const auto& move : path){
        cout << move.id << " " << move.dir << endl;
    }

    return 0;
}