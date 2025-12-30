#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <cstdlib>

using namespace std;

int n, m;
vector<vector<int>> cur; // current map
vector<vector<bool>> adj; // adjacency matrix from original map
vector<int> contact0; // number of adjacencies between color d and 0 (including boundary)

// directions: up, down, left, right
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};

bool is_inside(int i, int j) {
    return i >= 0 && i < n && j >= 0 && j < n;
}

bool is_boundary(int i, int j) {
    return i == 0 || i == n-1 || j == 0 || j == n-1;
}

// Check if a zero cell is a leaf (has exactly one zero neighbor, counting outside)
bool is_leaf(int i, int j) {
    if (cur[i][j] != 0) return false;
    int zero_cnt = 0;
    for (int dir = 0; dir < 4; dir++) {
        int ni = i + dx[dir];
        int nj = j + dy[dir];
        if (is_inside(ni, nj) && cur[ni][nj] == 0)
            zero_cnt++;
    }
    if (is_boundary(i, j))
        zero_cnt++; // outside is zero
    return zero_cnt == 1;
}

// Check if we can change cell (i,j) from 0 to color c.
// If possible, return true and the changes to contact0 in delta (size m+1, indices 1..m).
pair<bool, vector<int>> can_change(int i, int j, int c) {
    vector<int> delta(m+1, 0);
    bool on_boundary = is_boundary(i, j);

    int cnt_c_neighbors = 0;      // inside neighbors with color c
    int cnt_0_neighbors_inside = 0; // inside neighbors with color 0

    // Check adjacency legality and collect neighbor info
    for (int dir = 0; dir < 4; dir++) {
        int ni = i + dx[dir];
        int nj = j + dy[dir];
        int d;
        if (is_inside(ni, nj)) {
            d = cur[ni][nj];
            if (d == 0) cnt_0_neighbors_inside++;
            else if (d == c) cnt_c_neighbors++;
        } else {
            d = 0; // outside
        }

        if (d == c) continue;
        if (d == 0) {
            if (!adj[c][0]) return {false, {}};
        } else {
            if (!adj[c][d]) return {false, {}};
        }
    }

    // Compute changes to contact0
    for (int dir = 0; dir < 4; dir++) {
        int ni = i + dx[dir];
        int nj = j + dy[dir];
        if (is_inside(ni, nj)) {
            int d = cur[ni][nj];
            if (d != 0 && d != c) {
                delta[d] -= 1; // lose adjacency (0,d)
            }
        }
    }

    // Changes for color c
    delta[c] += cnt_0_neighbors_inside; // gain (c,0) from inside zeros
    delta[c] -= cnt_c_neighbors;        // lose (0,c) from c neighbors
    if (on_boundary) {
        delta[c] += 1; // gain (c,0) from boundary
    }

    // Verify that contact0 stays non-negative and for colors adjacent to 0 stays at least 1
    for (int d = 1; d <= m; d++) {
        int new_cnt = contact0[d] + delta[d];
        if (new_cnt < 0) return {false, {}};
        if (adj[0][d] && new_cnt < 1) return {false, {}};
    }

    return {true, delta};
}

int main() {
    // Input
    cin >> n >> m;
    cur.assign(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> cur[i][j];
        }
    }

    // Compute adjacency matrix from original map
    adj.assign(m+1, vector<bool>(m+1, false));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = cur[i][j];
            for (int dir = 0; dir < 4; dir++) {
                int ni = i + dx[dir];
                int nj = j + dy[dir];
                if (is_inside(ni, nj)) {
                    int d = cur[ni][nj];
                    if (c != d) {
                        adj[c][d] = true;
                        adj[d][c] = true;
                    }
                }
            }
            // boundary adjacency to color 0
            if (c != 0 && is_boundary(i, j)) {
                adj[c][0] = true;
                adj[0][c] = true;
            }
        }
    }

    // Compute initial contact0: for each color d, number of adjacencies with 0 (including boundary)
    contact0.assign(m+1, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int c = cur[i][j];
            if (c == 0) continue;
            for (int dir = 0; dir < 4; dir++) {
                int ni = i + dx[dir];
                int nj = j + dy[dir];
                if (is_inside(ni, nj) && cur[ni][nj] == 0) {
                    contact0[c]++;
                }
            }
            if (is_boundary(i, j)) {
                contact0[c]++; // adjacency to outside (0)
            }
        }
    }

    // Iterative improvement: repeatedly try to change leaf zero cells
    bool changed = true;
    while (changed) {
        changed = false;
        // Collect all leaf zero cells
        vector<pair<int,int>> leaves;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (cur[i][j] == 0 && is_leaf(i, j)) {
                    leaves.emplace_back(i, j);
                }
            }
        }

        // Try to change each leaf
        for (auto [i, j] : leaves) {
            if (cur[i][j] != 0) continue;
            // Gather candidate colors from non-zero neighbors
            set<int> cands;
            for (int dir = 0; dir < 4; dir++) {
                int ni = i + dx[dir];
                int nj = j + dy[dir];
                if (is_inside(ni, nj) && cur[ni][nj] != 0) {
                    cands.insert(cur[ni][nj]);
                }
            }
            for (int c : cands) {
                auto [ok, delta] = can_change(i, j, c);
                if (ok) {
                    // Apply the change
                    cur[i][j] = c;
                    for (int d = 1; d <= m; d++) {
                        contact0[d] += delta[d];
                    }
                    changed = true;
                    break; // only one change per cell
                }
            }
        }
    }

    // Output the resulting map
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cout << cur[i][j];
            if (j < n-1) cout << " ";
        }
        cout << endl;
    }

    return 0;
}