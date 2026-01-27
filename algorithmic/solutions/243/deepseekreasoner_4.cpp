#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <tuple>
#include <unordered_map>
#include <algorithm>
#include <cstring>

using namespace std;

const int dirs[4][2] = {{-1, 0}, {0, 1}, {1, 0}, {0, -1}}; // N, E, S, W

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    cin >> r >> c;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) {
        cin >> grid[i];
    }

    // Collect open cells
    vector<pair<int, int>> open;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                open.emplace_back(i+1, j+1); // store 1-indexed
            }
        }
    }

    int num_states = open.size() * 4;
    vector<int> state_i(num_states), state_j(num_states), state_dir(num_states);
    vector<int> obs(num_states);
    vector<int> left_id(num_states), right_id(num_states), step_id(num_states, -1);

    // id_at[i][j][d] -> state id, 1-indexed positions
    vector<vector<vector<int>>> id_at(r+2, vector<vector<int>>(c+2, vector<int>(4, -1)));
    int id = 0;
    for (auto& p : open) {
        int i = p.first, j = p.second;
        for (int d = 0; d < 4; ++d) {
            state_i[id] = i;
            state_j[id] = j;
            state_dir[id] = d;
            id_at[i][j][d] = id;
            ++id;
        }
    }

    // Precompute observations (distance to wall)
    for (int s = 0; s < num_states; ++s) {
        int i = state_i[s], j = state_j[s], d = state_dir[s];
        int di = dirs[d][0], dj = dirs[d][1];
        int cnt = 0;
        int ni = i + di, nj = j + dj;
        while (ni >= 1 && ni <= r && nj >= 1 && nj <= c && grid[ni-1][nj-1] == '.') {
            ++cnt;
            ni += di;
            nj += dj;
        }
        obs[s] = cnt;
    }

    // Precompute transitions
    for (int s = 0; s < num_states; ++s) {
        int i = state_i[s], j = state_j[s], d = state_dir[s];
        // left turn
        left_id[s] = id_at[i][j][(d+3)%4];
        // right turn
        right_id[s] = id_at[i][j][(d+1)%4];
        // step
        if (obs[s] > 0) {
            int ni = i + dirs[d][0], nj = j + dirs[d][1];
            step_id[s] = id_at[ni][nj][d];
        }
    }

    // Compute equivalence classes
    vector<int> class_id(num_states);
    unordered_map<int, int> obs_to_class;
    int class_counter = 0;
    for (int s = 0; s < num_states; ++s) {
        int d = obs[s];
        if (!obs_to_class.count(d)) {
            obs_to_class[d] = class_counter++;
        }
        class_id[s] = obs_to_class[d];
    }

    while (true) {
        map<tuple<int,int,int>, int> signature_to_new;
        int new_counter = 0;
        vector<tuple<int,int,int>> sig(num_states);
        for (int s = 0; s < num_states; ++s) {
            int left_c = class_id[left_id[s]];
            int right_c = class_id[right_id[s]];
            int step_c = (step_id[s] == -1) ? -1 : class_id[step_id[s]];
            sig[s] = {left_c, right_c, step_c};
            if (!signature_to_new.count(sig[s])) {
                signature_to_new[sig[s]] = new_counter++;
            }
        }
        if (new_counter == class_counter) break;
        for (int s = 0; s < num_states; ++s) {
            class_id[s] = signature_to_new[sig[s]];
        }
        class_counter = new_counter;
    }

    // For each class, check if it contains multiple positions
    vector<bool> class_has_multiple(class_counter, false);
    vector<int> class_first_i(class_counter, -1), class_first_j(class_counter, -1);
    for (int s = 0; s < num_states; ++s) {
        int cid = class_id[s];
        int i = state_i[s], j = state_j[s];
        if (class_first_i[cid] == -1) {
            class_first_i[cid] = i;
            class_first_j[cid] = j;
        } else {
            if (class_first_i[cid] != i || class_first_j[cid] != j) {
                class_has_multiple[cid] = true;
            }
        }
    }

    // Initial belief: all states
    vector<int> current;
    for (int s = 0; s < num_states; ++s) {
        current.push_back(s);
    }

    // First observation
    int d;
    cin >> d;
    if (d == -1) return 0;
    vector<int> tmp;
    for (int s : current) {
        if (obs[s] == d) {
            tmp.push_back(s);
        }
    }
    current = tmp;

    // Interaction loop
    while (true) {
        // Check if all positions are the same
        bool all_same = true;
        int pi = state_i[current[0]], pj = state_j[current[0]];
        for (size_t idx = 1; idx < current.size(); ++idx) {
            int s = current[idx];
            if (state_i[s] != pi || state_j[s] != pj) {
                all_same = false;
                break;
            }
        }
        if (all_same) {
            cout << "yes " << pi << " " << pj << endl;
            return 0;
        }

        // Check if current belief is a subset of an equivalence class with multiple positions
        bool same_class = true;
        int cid = class_id[current[0]];
        for (int s : current) {
            if (class_id[s] != cid) {
                same_class = false;
                break;
            }
        }
        if (same_class && class_has_multiple[cid]) {
            cout << "no" << endl;
            return 0;
        }

        // Check if step is safe
        bool step_safe = true;
        for (int s : current) {
            if (obs[s] == 0) {
                step_safe = false;
                break;
            }
        }

        // Evaluate each action
        int best_action = -1;
        int best_max_size = num_states + 1;
        // left
        {
            int cnt[101] = {0};
            for (int s : current) {
                int ns = left_id[s];
                ++cnt[obs[ns]];
            }
            int max_size = *max_element(cnt, cnt+101);
            if (max_size < best_max_size) {
                best_max_size = max_size;
                best_action = 0;
            }
        }
        // right
        {
            int cnt[101] = {0};
            for (int s : current) {
                int ns = right_id[s];
                ++cnt[obs[ns]];
            }
            int max_size = *max_element(cnt, cnt+101);
            if (max_size < best_max_size) {
                best_max_size = max_size;
                best_action = 1;
            }
        }
        // step (if safe)
        if (step_safe) {
            int cnt[101] = {0};
            for (int s : current) {
                int ns = step_id[s];
                ++cnt[obs[ns]];
            }
            int max_size = *max_element(cnt, cnt+101);
            if (max_size < best_max_size) {
                best_max_size = max_size;
                best_action = 2;
            }
        }

        // Output action
        if (best_action == 0) {
            cout << "left" << endl;
        } else if (best_action == 1) {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }

        // Read next observation
        cin >> d;
        if (d == -1) return 0;

        // Update belief
        tmp.clear();
        for (int s : current) {
            int ns;
            if (best_action == 0) ns = left_id[s];
            else if (best_action == 1) ns = right_id[s];
            else ns = step_id[s];
            if (obs[ns] == d) {
                tmp.push_back(ns);
            }
        }
        current = tmp;
    }

    return 0;
}