#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <queue>

using namespace std;

// Function to calculate the center ball index
int get_center_index(int k) {
    if (k == 0) return -1;
    // 0-based index
    // If odd (e.g. 1 -> 0, 3 -> 1), index is k/2
    // If even (e.g. 2 -> 1, 4 -> 2), index is k/2
    // wait: k=2 (0,1) -> larger is 1. 2/2 = 1.
    // k=4 (0,1,2,3) -> mid are 1,2. larger is 2. 4/2 = 2.
    // k=1 (0) -> 0. 1/2 = 0.
    // k=3 (0,1,2) -> 1. 3/2 = 1.
    // Formula is simply k / 2.
    return k / 2;
}

// Check if moving ball 'val' to basket 'dest' is valid
bool is_valid_move(const vector<int>& dest, int val) {
    int k = dest.size();
    int pos = 0;
    while (pos < k && dest[pos] < val) {
        pos++;
    }
    // New size will be k + 1
    // The ball becomes the center if its position equals the center index of the new configuration
    int new_center_idx = get_center_index(k + 1);
    return pos == new_center_idx;
}

// BFS Solver
void solve() {
    int N;
    if (!(cin >> N)) return;

    vector<vector<int>> start_state(3);
    for (int i = 1; i <= N; ++i) {
        start_state[0].push_back(i);
    }

    // Map to store visited states and reconstruct path
    // Key: state, Value: {parent_state_index, move_from, move_to}
    // Since map key is complex, we use an index for states
    map<vector<vector<int>>, int> visited;
    vector<pair<int, pair<int, int>>> parent; // index -> {parent_index, {from, to}}
    vector<vector<vector<int>>> states; // index -> state

    queue<int> q;

    visited[start_state] = 0;
    states.push_back(start_state);
    parent.push_back({-1, {-1, -1}});
    q.push(0);

    int final_state_idx = -1;

    while (!q.empty()) {
        int u_idx = q.front();
        q.pop();

        const auto& u = states[u_idx];

        // Check if target reached (all balls in basket 2, i.e., index 2)
        if (u[2].size() == N) {
            final_state_idx = u_idx;
            break;
        }

        // Try all moves
        for (int i = 0; i < 3; ++i) {
            if (u[i].empty()) continue;

            int c_idx = get_center_index(u[i].size());
            int val = u[i][c_idx];

            for (int j = 0; j < 3; ++j) {
                if (i == j) continue;

                if (is_valid_move(u[j], val)) {
                    vector<vector<int>> v = u;
                    // Remove from i
                    v[i].erase(v[i].begin() + c_idx);
                    // Add to j (maintain sorted order)
                    auto it = lower_bound(v[j].begin(), v[j].end(), val);
                    v[j].insert(it, val);

                    if (visited.find(v) == visited.end()) {
                        int v_idx = states.size();
                        visited[v] = v_idx;
                        states.push_back(v);
                        parent.push_back({u_idx, {i + 1, j + 1}});
                        q.push(v_idx);
                    }
                }
            }
        }
    }

    if (final_state_idx != -1) {
        vector<pair<int, int>> moves;
        int curr = final_state_idx;
        while (curr != 0) {
            moves.push_back(parent[curr].second);
            curr = parent[curr].first;
        }
        reverse(moves.begin(), moves.end());
        cout << moves.size() << endl;
        for (const auto& p : moves) {
            cout << p.first << " " << p.second << endl;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}