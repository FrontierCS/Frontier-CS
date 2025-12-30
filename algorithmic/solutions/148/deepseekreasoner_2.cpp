#include <bits/stdc++.h>
using namespace std;

pair<string, int> solve_with_K(int si, int sj,
                               const vector<vector<int>>& t,
                               const vector<vector<int>>& p,
                               const vector<pair<int,int>>& best_square,
                               int K) {
    int max_tile = best_square.size() - 1;
    vector<bool> visited_tile(max_tile+1, false);
    int cur_i = si, cur_j = sj;
    visited_tile[t[cur_i][cur_j]] = true;
    int score_total = p[cur_i][cur_j];
    string path = "";

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const char dir_char[4] = {'U', 'D', 'L', 'R'};

    while (true) {
        vector<vector<int>> dist(50, vector<int>(50, -1));
        vector<vector<pair<int,int>>> prev(50, vector<pair<int,int>>(50, {-1,-1}));
        queue<pair<int,int>> q;

        // Enqueue valid neighbors of current position
        for (int d = 0; d < 4; ++d) {
            int ni = cur_i + dx[d];
            int nj = cur_j + dy[d];
            if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
            if (visited_tile[t[ni][nj]]) continue;
            dist[ni][nj] = 1;
            prev[ni][nj] = {cur_i, cur_j};
            q.push({ni, nj});
        }

        // BFS
        while (!q.empty()) {
            auto [i, j] = q.front(); q.pop();
            for (int d = 0; d < 4; ++d) {
                int ni = i + dx[d];
                int nj = j + dy[d];
                if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
                if (visited_tile[t[ni][nj]]) continue;
                if (t[ni][nj] == t[i][j]) continue; // same tile consecutive move forbidden
                if (dist[ni][nj] != -1) continue;
                dist[ni][nj] = dist[i][j] + 1;
                prev[ni][nj] = {i, j};
                q.push({ni, nj});
            }
        }

        // Select target square
        int target_i = -1, target_j = -1;
        int best_score = -1e9;

        // First try: only squares that are the best for their tile
        for (int i = 0; i < 50; ++i) {
            for (int j = 0; j < 50; ++j) {
                if (dist[i][j] == -1) continue;
                if (make_pair(i, j) != best_square[t[i][j]]) continue;
                int sc = p[i][j] - K * dist[i][j];
                if (sc > best_score) {
                    best_score = sc;
                    target_i = i;
                    target_j = j;
                }
            }
        }

        // Fallback: any reachable square
        if (target_i == -1) {
            for (int i = 0; i < 50; ++i) {
                for (int j = 0; j < 50; ++j) {
                    if (dist[i][j] == -1) continue;
                    int sc = p[i][j] - K * dist[i][j];
                    if (sc > best_score) {
                        best_score = sc;
                        target_i = i;
                        target_j = j;
                    }
                }
            }
        }

        if (target_i == -1) break; // no reachable square

        // Find the first step towards the target
        int ci = target_i, cj = target_j;
        while (prev[ci][cj] != make_pair(cur_i, cur_j)) {
            tie(ci, cj) = prev[ci][cj];
        }

        // Determine move direction
        int di = ci - cur_i;
        int dj = cj - cur_j;
        char move;
        if (di == -1 && dj == 0) move = 'U';
        else if (di == 1 && dj == 0) move = 'D';
        else if (di == 0 && dj == -1) move = 'L';
        else if (di == 0 && dj == 1) move = 'R';
        else assert(false);

        path += move;
        cur_i = ci;
        cur_j = cj;
        visited_tile[t[cur_i][cur_j]] = true;
        score_total += p[cur_i][cur_j];
    }

    return {path, score_total};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;
    vector<vector<int>> t(50, vector<int>(50));
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            cin >> t[i][j];

    vector<vector<int>> p(50, vector<int>(50));
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            cin >> p[i][j];

    // Find maximum tile id
    int max_tile = 0;
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            max_tile = max(max_tile, t[i][j]);

    // Precompute the best square (max p) for each tile
    vector<pair<int,int>> best_square(max_tile+1, {-1,-1});
    for (int i = 0; i < 50; ++i) {
        for (int j = 0; j < 50; ++j) {
            int tid = t[i][j];
            if (best_square[tid].first == -1 || p[i][j] > p[best_square[tid].first][best_square[tid].second]) {
                best_square[tid] = {i, j};
            }
        }
    }

    // Try several values of K and choose the best path
    vector<int> Ks = {20, 30, 40, 50};
    string best_path;
    int best_score = -1;
    for (int K : Ks) {
        auto [path, score] = solve_with_K(si, sj, t, p, best_square, K);
        if (score > best_score) {
            best_score = score;
            best_path = path;
        }
    }

    cout << best_path << endl;
    return 0;
}