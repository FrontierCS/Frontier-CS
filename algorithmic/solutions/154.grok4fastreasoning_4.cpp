#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> get_pet_dist(const vector<vector<bool>>& blocked, const vector<int>& px, const vector<int>& py, int N) {
    vector<vector<int>> dist(31, vector<int>(31, -1));
    queue<pair<int, int>> q;
    for (int i = 0; i < N; i++) {
        int x = px[i], y = py[i];
        if (dist[x][y] == -1) {
            dist[x][y] = 0;
            q.push({x, y});
        }
    }
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 1 && nx <= 30 && ny >= 1 && ny <= 30 && !blocked[nx][ny] && dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                q.push({nx, ny});
            }
        }
    }
    return dist;
}

int main() {
    int N;
    cin >> N;
    vector<int> px(N), py(N), pt(N);
    for (int i = 0; i < N; i++) {
        cin >> px[i] >> py[i] >> pt[i];
    }
    int M;
    cin >> M;
    vector<int> hx(M), hy(M);
    for (int i = 0; i < M; i++) {
        cin >> hx[i] >> hy[i];
    }
    vector<vector<bool>> blocked(31, vector<bool>(31, false));
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char ucase[4] = {'U', 'D', 'L', 'R'};
    char lcase[4] = {'u', 'd', 'l', 'r'};
    for (int turn = 0; turn < 300; turn++) {
        auto pet_dist = get_pet_dist(blocked, px, py, N);
        string actions(M, '.');
        set<pair<int, int>> to_block;
        // First, decide blocks
        for (int i = 0; i < M; i++) {
            int x = hx[i], y = hy[i];
            vector<pair<int, int>> candidates; // score, d
            for (int d = 0; d < 4; d++) {
                int nx = x + dx[d], ny = y + dy[d];
                if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                if (blocked[nx][ny]) continue;
                // check occupancy
                bool has_occ = false;
                for (int j = 0; j < M; j++) {
                    if (hx[j] == nx && hy[j] == ny) has_occ = true;
                }
                for (int j = 0; j < N; j++) {
                    if (px[j] == nx && py[j] == ny) has_occ = true;
                }
                if (has_occ) continue;
                // check adj pet
                bool adj_pet = false;
                for (int dd = 0; dd < 4; dd++) {
                    int ax = nx + dx[dd], ay = ny + dy[dd];
                    if (ax >= 1 && ax <= 30 && ay >= 1 && ay <= 30) {
                        for (int j = 0; j < N; j++) {
                            if (px[j] == ax && py[j] == ay) {
                                adj_pet = true;
                                break;
                            }
                        }
                    }
                    if (adj_pet) break;
                }
                if (adj_pet) continue;
                // score
                int score = pet_dist[nx][ny];
                if (score == -1) score = INT_MAX / 2;
                candidates.emplace_back(score, d);
            }
            if (!candidates.empty()) {
                sort(candidates.begin(), candidates.end());
                int best_d = candidates[0].second;
                actions[i] = lcase[best_d];
                int nx = x + dx[best_d], ny = y + dy[best_d];
                to_block.insert({nx, ny});
            }
        }
        // Now, decide moves for those who didn't block
        for (int i = 0; i < M; i++) {
            if (actions[i] != '.') continue;
            int x = hx[i], y = hy[i];
            vector<pair<int, int>> move_cand; // score, d
            for (int d = 0; d < 4; d++) {
                int nx = x + dx[d], ny = y + dy[d];
                if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                if (blocked[nx][ny]) continue;
                if (to_block.count({nx, ny})) continue;
                int score = pet_dist[nx][ny];
                if (score == -1) score = INT_MAX / 2;
                move_cand.emplace_back(score, d);
            }
            if (!move_cand.empty()) {
                sort(move_cand.rbegin(), move_cand.rend());
                int best_d = move_cand[0].second;
                actions[i] = ucase[best_d];
            }
        }
        // Output
        cout << actions << endl;
        cout.flush();
        // Apply blocks
        for (auto p : to_block) {
            blocked[p.first][p.second] = true;
        }
        // Apply human moves
        for (int i = 0; i < M; i++) {
            char ac = actions[i];
            if (isupper(ac)) {
                int d = -1;
                if (ac == 'U') d = 0;
                else if (ac == 'D') d = 1;
                else if (ac == 'L') d = 2;
                else if (ac == 'R') d = 3;
                hx[i] += dx[d];
                hy[i] += dy[d];
            }
        }
        // Read and apply pet moves
        for (int i = 0; i < N; i++) {
            string s;
            cin >> s;
            int cx = px[i], cy = py[i];
            for (char c : s) {
                if (c == 'U') cx--;
                else if (c == 'D') cx++;
                else if (c == 'L') cy--;
                else if (c == 'R') cy++;
            }
            px[i] = cx;
            py[i] = cy;
        }
    }
    return 0;
}