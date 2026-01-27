#include <bits/stdc++.h>
using namespace std;

const int dx[4] = {-1, 0, 1, 0};
const int dy[4] = {0, 1, 0, -1};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) {
        cin >> grid[i];
    }

    // Precompute open cells
    vector<vector<bool>> open(r, vector<bool>(c, false));
    int openCount = 0;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                open[i][j] = true;
                openCount++;
            }
        }
    }

    // distance to wall in each direction
    vector<vector<vector<int>>> dist(r, vector<vector<int>>(c, vector<int>(4, 0)));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (!open[i][j]) continue;
            for (int d = 0; d < 4; ++d) {
                int x = i + dx[d], y = j + dy[d];
                int cnt = 0;
                while (x >= 0 && x < r && y >= 0 && y < c && open[x][y]) {
                    cnt++;
                    x += dx[d];
                    y += dy[d];
                }
                dist[i][j][d] = cnt;
            }
        }
    }

    // Assign state ids
    vector<vector<vector<int>>> stateId(r, vector<vector<int>>(c, vector<int>(4, -1)));
    int n = 0;
    vector<tuple<int,int,int>> statePos; // (i, j, dir)
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (open[i][j]) {
                for (int d = 0; d < 4; ++d) {
                    stateId[i][j][d] = n++;
                    statePos.emplace_back(i, j, d);
                }
            }
        }
    }

    // Precompute observation and transitions
    vector<int> obs(n);
    vector<int> nxt_left(n), nxt_right(n), nxt_step(n, -1);
    for (int idx = 0; idx < n; ++idx) {
        auto [i, j, dir] = statePos[idx];
        obs[idx] = dist[i][j][dir];
        // left
        int ndir = (dir + 3) % 4;
        nxt_left[idx] = stateId[i][j][ndir];
        // right
        ndir = (dir + 1) % 4;
        nxt_right[idx] = stateId[i][j][ndir];
        // step
        if (dist[i][j][dir] > 0) {
            int ni = i + dx[dir], nj = j + dy[dir];
            nxt_step[idx] = stateId[ni][nj][dir];
        }
    }

    // Compute equivalence classes by iterative refinement
    vector<int> class_id(n);
    {
        // initial classes based on observation
        vector<int> obs_vals = obs;
        sort(obs_vals.begin(), obs_vals.end());
        obs_vals.erase(unique(obs_vals.begin(), obs_vals.end()), obs_vals.end());
        unordered_map<int, int> obs_to_id;
        for (size_t i = 0; i < obs_vals.size(); ++i) {
            obs_to_id[obs_vals[i]] = i;
        }
        for (int i = 0; i < n; ++i) {
            class_id[i] = obs_to_id[obs[i]];
        }
        int num_classes = obs_vals.size();
        while (true) {
            vector<tuple<int,int,int,int>> signature(n);
            for (int i = 0; i < n; ++i) {
                int lb = (nxt_left[i] != -1) ? class_id[nxt_left[i]] : -1;
                int rb = (nxt_right[i] != -1) ? class_id[nxt_right[i]] : -1;
                int sb = (nxt_step[i] != -1) ? class_id[nxt_step[i]] : -1;
                signature[i] = {class_id[i], lb, rb, sb};
            }
            // group by signature
            map<tuple<int,int,int,int>, vector<int>> groups;
            for (int i = 0; i < n; ++i) {
                groups[signature[i]].push_back(i);
            }
            if ((int)groups.size() == num_classes) break;
            // assign new class ids
            int new_id = 0;
            for (auto& entry : groups) {
                for (int idx : entry.second) {
                    class_id[idx] = new_id;
                }
                new_id++;
            }
            num_classes = new_id;
        }
    }

    // Interaction
    vector<int> current_states;
    current_states.reserve(n);
    for (int i = 0; i < n; ++i) {
        current_states.push_back(i);
    }

    // First observation
    int d_in;
    cin >> d_in;
    if (d_in == -1) return 0;
    // Filter by initial observation
    vector<int> filtered;
    for (int idx : current_states) {
        if (obs[idx] == d_in) {
            filtered.push_back(idx);
        }
    }
    current_states = filtered;

    while (true) {
        if (current_states.empty()) {
            // should not happen
            break;
        }
        if (current_states.size() == 1) {
            int idx = current_states[0];
            auto [i, j, dir] = statePos[idx];
            cout << "yes " << i+1 << " " << j+1 << endl;
            break;
        }
        // Check if all states belong to the same equivalence class
        int cid = class_id[current_states[0]];
        bool all_same = true;
        for (int idx : current_states) {
            if (class_id[idx] != cid) {
                all_same = false;
                break;
            }
        }
        if (all_same) {
            cout << "no" << endl;
            break;
        }

        // Evaluate possible actions
        int best_action = -1; // 0=left,1=right,2=step
        int best_worst = INT_MAX;
        int best_groups = 0;

        for (int act = 0; act < 3; ++act) {
            if (act == 2) { // step
                bool safe = true;
                for (int idx : current_states) {
                    if (obs[idx] == 0) { // wall immediately in front
                        safe = false;
                        break;
                    }
                }
                if (!safe) continue;
            }
            int cnt[100] = {0};
            for (int idx : current_states) {
                int nidx = -1;
                if (act == 0) nidx = nxt_left[idx];
                else if (act == 1) nidx = nxt_right[idx];
                else if (act == 2) nidx = nxt_step[idx];
                int d = obs[nidx];
                cnt[d]++;
            }
            int worst = 0;
            int groups_cnt = 0;
            for (int d = 0; d < 100; ++d) {
                if (cnt[d] > 0) {
                    groups_cnt++;
                    if (cnt[d] > worst) worst = cnt[d];
                }
            }
            if (worst < best_worst || (worst == best_worst && groups_cnt > best_groups)) {
                best_worst = worst;
                best_groups = groups_cnt;
                best_action = act;
            }
        }

        // fallback (should not happen)
        if (best_action == -1) best_action = 0;

        // Output action
        if (best_action == 0) cout << "left" << endl;
        else if (best_action == 1) cout << "right" << endl;
        else if (best_action == 2) cout << "step" << endl;

        // Read observation
        cin >> d_in;
        if (d_in == -1) break;

        // Update current states
        vector<int> new_states;
        for (int idx : current_states) {
            int nidx = -1;
            if (best_action == 0) nidx = nxt_left[idx];
            else if (best_action == 1) nidx = nxt_right[idx];
            else if (best_action == 2) nidx = nxt_step[idx];
            if (obs[nidx] == d_in) {
                new_states.push_back(nidx);
            }
        }
        current_states = new_states;
    }

    return 0;
}