#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

const vector<pair<int, int>> q_cells = {
    {0,0}, {0,4}, {0,8}, {0,9}, {0,10},
    {1,0}, {1,1}, {1,3}, {1,4}, {1,8}, {1,11},
    {2,1}, {2,3}, {2,5}, {2,8},
    {3,1}, {3,3}, {3,5}, {3,8},
    {4,1}, {4,3}, {4,5}, {4,8},
    {5,5},
    {7,0}, {7,2}, {7,3}, {7,5}, {7,7}, {7,9}, {7,10}, {7,11},
    {8,0}, {8,2}, {8,6}, {8,8}, {8,11},
    {9,1}, {9,4}, {9,6}, {9,8}, {9,9}, {9,10},
    {10,0}, {10,2}, {10,4}, {10,7}, {10,8}, {10,11},
    {11,7}, {11,8}, {11,10}, {11,11}
};

const int N = 53;
const int MIN_DIST_STEP = 1;
const int MAX_DIST_STEP = 3;

int dists[N][N];
int path[N];
bool visited[N];

bool find_path(int u_idx, int k) {
    path[k] = u_idx;
    visited[u_idx] = true;

    if (k == N - 1) {
        return true;
    }

    map<int, vector<int>> dist_map;
    for (int v_idx = 0; v_idx < N; ++v_idx) {
        if (!visited[v_idx]) {
            dist_map[dists[u_idx][v_idx]].push_back(v_idx);
        }
    }

    for (auto const& [dist, nodes] : dist_map) {
        if (dist >= MIN_DIST_STEP && dist <= MAX_DIST_STEP && nodes.size() == 1) {
            int v_idx = nodes[0];
            if (find_path(v_idx, k + 1)) {
                return true;
            }
        }
    }

    visited[u_idx] = false;
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int task_type;
    cin >> task_type;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dists[i][j] = abs(q_cells[i].first - q_cells[j].first) +
                          abs(q_cells[i].second - q_cells[j].second);
        }
    }

    int start_idx = -1;
    for (int i = 0; i < N; ++i) {
        if (q_cells[i].first == 0 && q_cells[i].second == 0) {
            start_idx = i;
            break;
        }
    }

    fill(visited, visited + N, false);

    if (find_path(start_idx, 0)) {
        vector<string> grid(12, string(12, ' '));

        for (int i = 0; i < N - 1; ++i) {
            int u_idx = path[i];
            int v_idx = path[i+1];
            int r = q_cells[u_idx].first;
            int c = q_cells[u_idx].second;
            grid[r][c] = to_string(dists[u_idx][v_idx])[0];
        }

        int last_u_idx = path[N - 1];
        int r = q_cells[last_u_idx].first;
        int c = q_cells[last_u_idx].second;
        if (task_type == 0) {
            grid[r][c] = '0';
        } else {
            grid[r][c] = '1';
        }

        for (int i = 0; i < 12; ++i) {
            cout << grid[i] << (i == 11 ? "" : "\n");
        }
    }

    return 0;
}