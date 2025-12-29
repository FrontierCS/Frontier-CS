#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>
#include <cstring>

using namespace std;

const int dx[8] = {-2, -2, -1, -1, 1, 1, 2, 2};
const int dy[8] = {-1, 1, -2, 2, -2, 2, -1, 1};

vector<pair<int,int>> deterministic_greedy(int N, int sr, int sc, const vector<vector<int>>& init_deg) {
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    vector<vector<int>> deg = init_deg;
    vector<pair<int,int>> path;
    int r = sr, c = sc;
    visited[r][c] = true;
    path.emplace_back(r, c);
    // decrease degree of neighbors of start
    for (int d = 0; d < 8; ++d) {
        int nr = r + dx[d], nc = c + dy[d];
        if (nr >= 0 && nr < N && nc >= 0 && nc < N)
            deg[nr][nc]--;
    }
    int center = N - 1;  // 2*center_coordinate
    while (true) {
        vector<array<int,4>> candidates; // degree, -dist2, row, col
        for (int d = 0; d < 8; ++d) {
            int nr = r + dx[d], nc = c + dy[d];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                int degree = deg[nr][nc];
                int dr = 2 * nr - center;
                int dc = 2 * nc - center;
                int dist2 = dr * dr + dc * dc;
                candidates.push_back({degree, -dist2, nr, nc});
            }
        }
        if (candidates.empty()) break;
        sort(candidates.begin(), candidates.end()); // lexicographic
        int nr = candidates[0][2], nc = candidates[0][3];
        visited[nr][nc] = true;
        path.emplace_back(nr, nc);
        // update degree of neighbors of new square
        for (int d = 0; d < 8; ++d) {
            int nnr = nr + dx[d], nnc = nc + dy[d];
            if (nnr >= 0 && nnr < N && nnc >= 0 && nnc < N)
                deg[nnr][nnc]--;
        }
        r = nr; c = nc;
    }
    return path;
}

vector<pair<int,int>> randomized_greedy(int N, int sr, int sc, const vector<vector<int>>& init_deg, mt19937& rng) {
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    vector<vector<int>> deg = init_deg;
    vector<pair<int,int>> path;
    int r = sr, c = sc;
    visited[r][c] = true;
    path.emplace_back(r, c);
    for (int d = 0; d < 8; ++d) {
        int nr = r + dx[d], nc = c + dy[d];
        if (nr >= 0 && nr < N && nc >= 0 && nc < N)
            deg[nr][nc]--;
    }
    while (true) {
        vector<pair<int,int>> candidates;
        vector<int> cand_deg;
        int min_deg = 9;
        for (int d = 0; d < 8; ++d) {
            int nr = r + dx[d], nc = c + dy[d];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                int dg = deg[nr][nc];
                candidates.emplace_back(nr, nc);
                cand_deg.push_back(dg);
                if (dg < min_deg) min_deg = dg;
            }
        }
        if (candidates.empty()) break;
        vector<pair<int,int>> min_candidates;
        for (size_t i = 0; i < candidates.size(); ++i) {
            if (cand_deg[i] == min_deg)
                min_candidates.push_back(candidates[i]);
        }
        uniform_int_distribution<int> dist(0, min_candidates.size() - 1);
        int idx = dist(rng);
        int nr = min_candidates[idx].first, nc = min_candidates[idx].second;
        visited[nr][nc] = true;
        path.emplace_back(nr, nc);
        for (int d = 0; d < 8; ++d) {
            int nnr = nr + dx[d], nnc = nc + dy[d];
            if (nnr >= 0 && nnr < N && nnc >= 0 && nnc < N)
                deg[nnr][nnc]--;
        }
        r = nr; c = nc;
    }
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, r0, c0;
    cin >> N >> r0 >> c0;
    r0--; c0--; // to 0-indexed

    // precompute initial degrees
    vector<vector<int>> init_deg(N, vector<int>(N, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int cnt = 0;
            for (int d = 0; d < 8; ++d) {
                int ni = i + dx[d], nj = j + dy[d];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N) cnt++;
            }
            init_deg[i][j] = cnt;
        }
    }

    // deterministic attempt
    vector<pair<int,int>> best_path = deterministic_greedy(N, r0, c0, init_deg);
    int best_len = best_path.size();

    // if not full board, try randomized attempts
    const int MAX_RANDOM_ITER = 20;
    if (best_len < N * N) {
        mt19937 rng(time(0));
        for (int iter = 0; iter < MAX_RANDOM_ITER; ++iter) {
            vector<pair<int,int>> path = randomized_greedy(N, r0, c0, init_deg, rng);
            if (path.size() > best_len) {
                best_len = path.size();
                best_path = move(path);
                if (best_len == N * N) break; // found full tour
            }
        }
    }

    // output
    cout << best_len << '\n';
    for (auto& p : best_path) {
        cout << p.first + 1 << ' ' << p.second + 1 << '\n';
    }
    return 0;
}