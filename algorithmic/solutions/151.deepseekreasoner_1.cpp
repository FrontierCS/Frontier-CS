#include <iostream>
#include <vector>
#include <queue>
#include <bitset>
#include <string>
#include <algorithm>
#include <tuple>
#include <utility>
#include <climits>
#include <cstring>

using namespace std;

const int MAX_N = 69;
const int MAX_R = MAX_N * MAX_N; // at most 4761

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    // Assign an index to each road square
    vector<vector<int>> id(N, vector<int>(N, -1));
    vector<vector<int>> weight(N, vector<int>(N, 0));
    vector<pair<int, int>> pos;
    int total_road = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                id[i][j] = total_road++;
                pos.push_back({i, j});
                weight[i][j] = grid[i][j] - '0';
            }
        }
    }

    // Build horizontal segments
    vector<vector<int>> horiz_segments;
    vector<bitset<MAX_R>> horiz_bits;
    vector<vector<int>> horiz_id(N, vector<int>(N, -1));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ) {
            if (grid[i][j] == '#') { ++j; continue; }
            vector<int> seg;
            int start_j = j;
            while (j < N && grid[i][j] != '#') {
                seg.push_back(id[i][j]);
                horiz_id[i][j] = horiz_segments.size();
                ++j;
            }
            horiz_segments.push_back(seg);
            bitset<MAX_R> bs;
            for (int idx : seg) bs.set(idx);
            horiz_bits.push_back(bs);
        }
    }

    // Build vertical segments
    vector<vector<int>> vert_segments;
    vector<bitset<MAX_R>> vert_bits;
    vector<vector<int>> vert_id(N, vector<int>(N, -1));
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ) {
            if (grid[i][j] == '#') { ++i; continue; }
            vector<int> seg;
            int start_i = i;
            while (i < N && grid[i][j] != '#') {
                seg.push_back(id[i][j]);
                vert_id[i][j] = vert_segments.size();
                ++i;
            }
            vert_segments.push_back(seg);
            bitset<MAX_R> bs;
            for (int idx : seg) bs.set(idx);
            vert_bits.push_back(bs);
        }
    }

    // Coverage state
    bitset<MAX_R> covered;
    vector<bool> horiz_covered(horiz_segments.size(), false);
    vector<bool> vert_covered(vert_segments.size(), false);

    int start_idx = id[si][sj];
    int h0 = horiz_id[si][sj];
    int v0 = vert_id[si][sj];
    covered |= horiz_bits[h0];
    covered |= vert_bits[v0];
    horiz_covered[h0] = true;
    vert_covered[v0] = true;

    string moves;
    int ci = si, cj = sj;

    const vector<pair<int,int>> dirs = {{-1,0}, {1,0}, {0,-1}, {0,1}};
    const vector<char> dir_char = {'U', 'D', 'L', 'R'};

    // Main greedy loop
    while ((int)covered.count() < total_road) {
        int best_gain = -1;
        char best_dir = '?';
        int best_weight = 10;

        // Evaluate the four neighbors
        for (int d = 0; d < 4; ++d) {
            int ni = ci + dirs[d].first;
            int nj = cj + dirs[d].second;
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (grid[ni][nj] == '#') continue;
            int nid = id[ni][nj];
            int h_id = horiz_id[ni][nj];
            int v_id = vert_id[ni][nj];

            bitset<MAX_R> temp = covered;
            temp |= horiz_bits[h_id];
            temp |= vert_bits[v_id];
            int gain = (int)(temp.count() - covered.count());
            int w = weight[ni][nj];

            if (gain > best_gain || (gain == best_gain && w < best_weight)) {
                best_gain = gain;
                best_dir = dir_char[d];
                best_weight = w;
            }
        }

        if (best_gain > 0) {
            // Take the best move
            moves += best_dir;
            if (best_dir == 'U') --ci;
            else if (best_dir == 'D') ++ci;
            else if (best_dir == 'L') --cj;
            else ++cj;

            int nid = id[ci][cj];
            int h_id = horiz_id[ci][cj];
            int v_id = vert_id[ci][cj];

            if (!horiz_covered[h_id]) {
                covered |= horiz_bits[h_id];
                horiz_covered[h_id] = true;
            }
            if (!vert_covered[v_id]) {
                covered |= vert_bits[v_id];
                vert_covered[v_id] = true;
            }
        } else {
            // No immediate gain: BFS to the nearest square that would give gain
            vector<vector<bool>> visited(N, vector<bool>(N, false));
            vector<vector<pair<int,int>>> parent(N, vector<pair<int,int>>(N, {-1,-1}));
            queue<pair<int,int>> q;
            q.push({ci, cj});
            visited[ci][cj] = true;
            int ti = -1, tj = -1;

            while (!q.empty()) {
                auto [i, j] = q.front(); q.pop();
                int idx = id[i][j];
                int h_id = horiz_id[i][j];
                int v_id = vert_id[i][j];
                bitset<MAX_R> temp = covered;
                temp |= horiz_bits[h_id];
                temp |= vert_bits[v_id];
                int gain = (int)(temp.count() - covered.count());
                if (gain > 0) {
                    ti = i; tj = j;
                    break;
                }
                for (int d = 0; d < 4; ++d) {
                    int ni = i + dirs[d].first;
                    int nj = j + dirs[d].second;
                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                    if (grid[ni][nj] == '#') continue;
                    if (visited[ni][nj]) continue;
                    visited[ni][nj] = true;
                    parent[ni][nj] = {i, j};
                    q.push({ni, nj});
                }
            }

            // Should always find such a square
            if (ti == -1) break;

            // Reconstruct the first step toward that square
            int ni = ti, nj = tj;
            while (!(parent[ni][nj].first == ci && parent[ni][nj].second == cj)) {
                int pi = parent[ni][nj].first;
                int pj = parent[ni][nj].second;
                ni = pi; nj = pj;
            }

            char dir;
            if (ni == ci-1 && nj == cj) dir = 'U';
            else if (ni == ci+1 && nj == cj) dir = 'D';
            else if (ni == ci && nj == cj-1) dir = 'L';
            else dir = 'R';

            moves += dir;
            ci = ni; cj = nj;
            // No new coverage because gain was zero
        }
    }

    // Return to start via shortest weighted path
    if (ci != si || cj != sj) {
        const long long INF = 1e18;
        vector<vector<long long>> dist(N, vector<long long>(N, INF));
        vector<vector<pair<int,int>>> parent(N, vector<pair<int,int>>(N, {-1,-1}));
        vector<vector<char>> parent_dir(N, vector<char>(N, '?'));
        dist[ci][cj] = 0;
        using State = tuple<long long, int, int>;
        priority_queue<State, vector<State>, greater<State>> pq;
        pq.push({0, ci, cj});

        while (!pq.empty()) {
            auto [cost, i, j] = pq.top(); pq.pop();
            if (cost > dist[i][j]) continue;
            if (i == si && j == sj) break;
            for (int d = 0; d < 4; ++d) {
                int ni = i + dirs[d].first;
                int nj = j + dirs[d].second;
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                if (grid[ni][nj] == '#') continue;
                long long new_cost = cost + weight[ni][nj];
                if (new_cost < dist[ni][nj]) {
                    dist[ni][nj] = new_cost;
                    parent[ni][nj] = {i, j};
                    parent_dir[ni][nj] = dir_char[d];
                    pq.push({new_cost, ni, nj});
                }
            }
        }

        // Reconstruct path from start back to current (then reverse)
        vector<char> return_moves;
        int i = si, j = sj;
        while (!(i == ci && j == cj)) {
            return_moves.push_back(parent_dir[i][j]);
            int pi = parent[i][j].first;
            int pj = parent[i][j].second;
            i = pi; j = pj;
        }
        reverse(return_moves.begin(), return_moves.end());
        moves += string(return_moves.begin(), return_moves.end());
    }

    cout << moves << endl;
    return 0;
}