#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <unordered_set>
#include <cstdint>
#include <numeric>
#include <climits>

using namespace std;

const int dirs[4][2] = {{-1, 0}, {0, 1}, {1, 0}, {0, -1}}; // N, E, S, W

int main() {
    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // list of open squares
    vector<pair<int,int>> open_list;
    vector<vector<int>> pos_id(r, vector<int>(c, -1));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                pos_id[i][j] = open_list.size();
                open_list.emplace_back(i, j);
            }
        }
    }
    int open_count = open_list.size();
    int N = open_count * 4; // number of states (position + direction)

    // state index -> (i, j, dir)
    vector<int> state_i(N), state_j(N), state_dir(N);
    for (int idx = 0; idx < open_count; ++idx) {
        int i = open_list[idx].first, j = open_list[idx].second;
        for (int d = 0; d < 4; ++d) {
            int s = idx * 4 + d;
            state_i[s] = i;
            state_j[s] = j;
            state_dir[s] = d;
        }
    }

    // precompute view distances for each open square and direction
    vector<vector<int>> view(open_count, vector<int>(4));
    for (int idx = 0; idx < open_count; ++idx) {
        int i = open_list[idx].first, j = open_list[idx].second;
        for (int d = 0; d < 4; ++d) {
            int step = 0;
            int ni = i + dirs[d][0], nj = j + dirs[d][1];
            while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                ++step;
                ni += dirs[d][0];
                nj += dirs[d][1];
            }
            view[idx][d] = step;
        }
    }

    // precompute next_state and obs for each action: 0=left, 1=right, 2=step
    vector<vector<int>> next_state(3, vector<int>(N, -1));
    vector<vector<int>> obs(3, vector<int>(N, -1));
    for (int s = 0; s < N; ++s) {
        int i = state_i[s], j = state_j[s], dir = state_dir[s];
        int idx = s / 4;

        // left
        int new_dir = (dir + 3) % 4;
        next_state[0][s] = idx * 4 + new_dir;
        obs[0][s] = view[idx][new_dir];

        // right
        new_dir = (dir + 1) % 4;
        next_state[1][s] = idx * 4 + new_dir;
        obs[1][s] = view[idx][new_dir];

        // step
        int ni = i + dirs[dir][0], nj = j + dirs[dir][1];
        if (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
            int new_idx = pos_id[ni][nj];
            next_state[2][s] = new_idx * 4 + dir;
            obs[2][s] = view[new_idx][dir];
        }
    }

    // initial active states: all states
    vector<int> active(N);
    iota(active.begin(), active.end(), 0);

    unordered_set<uint64_t> seen_hashes;

    while (true) {
        // check if all active states share the same position
        int first_pos = active[0] / 4;
        bool same_pos = true;
        for (int s : active) {
            if (s / 4 != first_pos) {
                same_pos = false;
                break;
            }
        }
        if (same_pos) {
            int i = open_list[first_pos].first + 1;
            int j = open_list[first_pos].second + 1;
            cout << "yes " << i << " " << j << endl;
            return 0;
        }

        // compute hash of the set of positions (ignoring directions) to detect cycles
        vector<bool> pos_seen(open_count, false);
        uint64_t hash = 0;
        const uint64_t k = 0x9e3779b9;
        for (int s : active) {
            int pid = s / 4;
            if (!pos_seen[pid]) {
                pos_seen[pid] = true;
                hash ^= (uint64_t(pid) * k + 0x6a09e667);
            }
        }
        if (seen_hashes.count(hash)) {
            cout << "no" << endl;
            return 0;
        }
        seen_hashes.insert(hash);

        // evaluate available actions
        bool step_allowed = true;
        for (int s : active) {
            if (next_state[2][s] == -1) {
                step_allowed = false;
                break;
            }
        }

        vector<int> worst(3, INT_MAX);
        vector<int> cnt(100, 0);

        // left
        fill(cnt.begin(), cnt.end(), 0);
        for (int s : active) {
            int d = obs[0][s];
            if (d >= 0 && d < 100) ++cnt[d];
        }
        worst[0] = *max_element(cnt.begin(), cnt.end());

        // right
        fill(cnt.begin(), cnt.end(), 0);
        for (int s : active) {
            int d = obs[1][s];
            if (d >= 0 && d < 100) ++cnt[d];
        }
        worst[1] = *max_element(cnt.begin(), cnt.end());

        // step
        if (step_allowed) {
            fill(cnt.begin(), cnt.end(), 0);
            for (int s : active) {
                int d = obs[2][s];
                if (d >= 0 && d < 100) ++cnt[d];
            }
            worst[2] = *max_element(cnt.begin(), cnt.end());
        }

        // choose action: minimize worst-case remaining states, prefer step in case of tie
        int best_action = -1;
        int best_val = INT_MAX;
        for (int a : {2, 0, 1}) {
            if (worst[a] < best_val) {
                best_val = worst[a];
                best_action = a;
            }
        }

        string cmd;
        if (best_action == 0) cmd = "left";
        else if (best_action == 1) cmd = "right";
        else cmd = "step";
        cout << cmd << endl;

        int d_obs;
        cin >> d_obs;
        if (d_obs == -1) break;

        // update active set
        vector<int> new_active;
        for (int s : active) {
            if (obs[best_action][s] == d_obs) {
                int ns = next_state[best_action][s];
                if (ns != -1) {
                    new_active.push_back(ns);
                }
            }
        }
        if (new_active.empty()) {
            // inconsistency – should not happen
            cout << "no" << endl;
            return 0;
        }
        active.swap(new_active);
    }

    return 0;
}