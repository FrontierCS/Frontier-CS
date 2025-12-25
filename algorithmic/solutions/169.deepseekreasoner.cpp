#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <ctime>
#include <cstdlib>
#include <cstdio>

using namespace std;

int main() {
    int N;
    cin >> N;
    vector<string> board(N);
    for (int i = 0; i < N; ++i) {
        cin >> board[i];
    }

    // Collect positions of Oni and Fukunokami
    vector<pair<int,int>> oni_pos;
    vector<vector<bool>> isFuku(N, vector<bool>(N, false));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'o') {
                isFuku[i][j] = true;
            } else if (board[i][j] == 'x') {
                oni_pos.emplace_back(i, j);
            }
        }
    }

    int M = oni_pos.size(); // M = 40

    // For each Oni, determine safe directions
    vector<vector<char>> safe_dirs(M);
    for (int idx = 0; idx < M; ++idx) {
        int i = oni_pos[idx].first;
        int j = oni_pos[idx].second;
        bool up = true, down = true, left = true, right = true;
        for (int k = 0; k < i; ++k) if (isFuku[k][j]) { up = false; break; }
        for (int k = i+1; k < N; ++k) if (isFuku[k][j]) { down = false; break; }
        for (int k = 0; k < j; ++k) if (isFuku[i][k]) { left = false; break; }
        for (int k = j+1; k < N; ++k) if (isFuku[i][k]) { right = false; break; }
        if (up) safe_dirs[idx].push_back('U');
        if (down) safe_dirs[idx].push_back('D');
        if (left) safe_dirs[idx].push_back('L');
        if (right) safe_dirs[idx].push_back('R');
    }

    // Randomized greedy assignment
    vector<char> best_assignment(M);
    int best_cost = 1e9;
    mt19937 rng(time(0));

    for (int iter = 0; iter < 1000; ++iter) {
        // Shuffle Oni indices
        vector<int> order(M);
        for (int i = 0; i < M; ++i) order[i] = i;
        shuffle(order.begin(), order.end(), rng);

        vector<int> up_max(N, -1);
        vector<int> down_min(N, N);
        vector<int> left_max(N, -1);
        vector<int> right_min(N, N);
        vector<char> assign(M);

        for (int idx : order) {
            int i = oni_pos[idx].first;
            int j = oni_pos[idx].second;

            // Compute marginal costs for each safe direction
            int costU = (i > up_max[j]) ? 2 * (i - up_max[j]) : 0;
            int costD = (i < down_min[j]) ? 2 * (down_min[j] - i) : 0;
            int costL = (j > left_max[i]) ? 2 * (j - left_max[i]) : 0;
            int costR = (j < right_min[i]) ? 2 * (right_min[i] - j) : 0;

            // Choose direction with minimum marginal cost
            int best_cost_dir = 1e9;
            char best_dir;
            for (char dir : safe_dirs[idx]) {
                int cost;
                if (dir == 'U') cost = costU;
                else if (dir == 'D') cost = costD;
                else if (dir == 'L') cost = costL;
                else cost = costR;
                if (cost < best_cost_dir) {
                    best_cost_dir = cost;
                    best_dir = dir;
                }
            }

            assign[idx] = best_dir;
            // Update extremes
            if (best_dir == 'U') {
                up_max[j] = max(up_max[j], i);
            } else if (best_dir == 'D') {
                down_min[j] = min(down_min[j], i);
            } else if (best_dir == 'L') {
                left_max[i] = max(left_max[i], j);
            } else if (best_dir == 'R') {
                right_min[i] = min(right_min[i], j);
            }
        }

        // Compute total cost for this assignment
        int total = 0;
        for (int j = 0; j < N; ++j) {
            if (up_max[j] != -1) total += 2 * (up_max[j] + 1);
            if (down_min[j] != N) total += 2 * (N - down_min[j]);
        }
        for (int i = 0; i < N; ++i) {
            if (left_max[i] != -1) total += 2 * (left_max[i] + 1);
            if (right_min[i] != N) total += 2 * (N - right_min[i]);
        }

        if (total < best_cost) {
            best_cost = total;
            best_assignment = assign;
        }
    }

    // Group assigned Oni by direction
    vector<vector<int>> up_lists(N);
    vector<vector<int>> down_lists(N);
    vector<vector<int>> left_lists(N);
    vector<vector<int>> right_lists(N);
    for (int idx = 0; idx < M; ++idx) {
        int i = oni_pos[idx].first;
        int j = oni_pos[idx].second;
        char dir = best_assignment[idx];
        if (dir == 'U') up_lists[j].push_back(i);
        else if (dir == 'D') down_lists[j].push_back(i);
        else if (dir == 'L') left_lists[i].push_back(j);
        else if (dir == 'R') right_lists[i].push_back(j);
    }

    // Boolean array to track which Oni are still present
    vector<vector<bool>> present(N, vector<bool>(N, false));
    for (auto& p : oni_pos) {
        present[p.first][p.second] = true;
    }

    // Store the sequence of moves
    vector<pair<char, int>> moves;

    // Process columns: first upward batches, then downward batches
    for (int j = 0; j < N; ++j) {
        // Up batch for column j
        if (!up_lists[j].empty()) {
            vector<int> rows;
            for (int i : up_lists[j]) {
                if (present[i][j]) rows.push_back(i);
            }
            if (!rows.empty()) {
                int max_i = *max_element(rows.begin(), rows.end());
                int k = max_i + 1;
                for (int t = 0; t < k; ++t) moves.emplace_back('U', j);
                for (int t = 0; t < k; ++t) moves.emplace_back('D', j);
                // Remove all Oni in column j with row <= max_i
                for (auto& p : oni_pos) {
                    int r = p.first, c = p.second;
                    if (c == j && r <= max_i && present[r][c]) {
                        present[r][c] = false;
                    }
                }
            }
        }
        // Down batch for column j
        if (!down_lists[j].empty()) {
            vector<int> rows;
            for (int i : down_lists[j]) {
                if (present[i][j]) rows.push_back(i);
            }
            if (!rows.empty()) {
                int min_i = *min_element(rows.begin(), rows.end());
                int k = N - min_i;
                for (int t = 0; t < k; ++t) moves.emplace_back('D', j);
                for (int t = 0; t < k; ++t) moves.emplace_back('U', j);
                // Remove all Oni in column j with row >= min_i
                for (auto& p : oni_pos) {
                    int r = p.first, c = p.second;
                    if (c == j && r >= min_i && present[r][c]) {
                        present[r][c] = false;
                    }
                }
            }
        }
    }

    // Process rows: first left batches, then right batches
    for (int i = 0; i < N; ++i) {
        // Left batch for row i
        if (!left_lists[i].empty()) {
            vector<int> cols;
            for (int j : left_lists[i]) {
                if (present[i][j]) cols.push_back(j);
            }
            if (!cols.empty()) {
                int max_j = *max_element(cols.begin(), cols.end());
                int k = max_j + 1;
                for (int t = 0; t < k; ++t) moves.emplace_back('L', i);
                for (int t = 0; t < k; ++t) moves.emplace_back('R', i);
                // Remove all Oni in row i with column <= max_j
                for (auto& p : oni_pos) {
                    int r = p.first, c = p.second;
                    if (r == i && c <= max_j && present[r][c]) {
                        present[r][c] = false;
                    }
                }
            }
        }
        // Right batch for row i
        if (!right_lists[i].empty()) {
            vector<int> cols;
            for (int j : right_lists[i]) {
                if (present[i][j]) cols.push_back(j);
            }
            if (!cols.empty()) {
                int min_j = *min_element(cols.begin(), cols.end());
                int k = N - min_j;
                for (int t = 0; t < k; ++t) moves.emplace_back('R', i);
                for (int t = 0; t < k; ++t) moves.emplace_back('L', i);
                // Remove all Oni in row i with column >= min_j
                for (auto& p : oni_pos) {
                    int r = p.first, c = p.second;
                    if (r == i && c >= min_j && present[r][c]) {
                        present[r][c] = false;
                    }
                }
            }
        }
    }

    // Output the moves
    printf("%d\n", (int)moves.size());
    for (auto& move : moves) {
        printf("%c %d\n", move.first, move.second);
    }

    return 0;
}