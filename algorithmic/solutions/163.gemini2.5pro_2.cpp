#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <chrono>
#include <random>
#include <queue>
#include <tuple>
#include <map>

using namespace std;

const int N = 50;
const int M = 100;

int n_fixed = N, m_fixed = M;
int initial_grid[N][N];
bool target_adj[M + 1][M + 1];
bool is_coastal[M + 1];

struct Timer {
    chrono::steady_clock::time_point start_time;
    Timer() {
        start_time = chrono::steady_clock::now();
    }
    long long get_ms() {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count();
    }
};

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

struct State {
    vector<pair<int, int>> pos;
    long long score;

    State() : pos(M + 1), score(-1) {}
};

int temp_grid[N][N];
bool created_adj[M + 1][M + 1];

long long calculate_energy(State& s) {
    for (int i = 0; i < n_fixed; ++i) {
        for (int j = 0; j < n_fixed; ++j) {
            temp_grid[i][j] = 0;
        }
    }
    queue<pair<int, int>> q;
    for (int k = 1; k <= m_fixed; ++k) {
        temp_grid[s.pos[k].first][s.pos[k].second] = k;
        q.push(s.pos[k]);
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int r = curr.first;
        int c = curr.second;
        int color = temp_grid[r][c];

        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            if (nr >= 0 && nr < n_fixed && nc >= 0 && nc < n_fixed && temp_grid[nr][nc] == 0) {
                temp_grid[nr][nc] = color;
                q.push({nr, nc});
            }
        }
    }

    for (int i = 0; i <= m_fixed; ++i) {
        for (int j = 0; j <= m_fixed; ++j) {
            created_adj[i][j] = false;
        }
    }

    for (int i = 0; i < n_fixed; ++i) {
        for (int j = 0; j < n_fixed; ++j) {
            int c1 = temp_grid[i][j];
            if (i == 0 || i == n_fixed - 1 || j == 0 || j == n_fixed - 1) {
                created_adj[c1][0] = created_adj[0][c1] = true;
            }
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (ni >= 0 && ni < n_fixed && nj >= 0 && nj < n_fixed) {
                    int c2 = temp_grid[ni][nj];
                    if (c1 != c2) {
                        created_adj[c1][c2] = created_adj[c2][c1] = true;
                    }
                }
            }
        }
    }

    long long missing_adj = 0, extra_adj = 0;
    for (int i = 0; i <= m_fixed; ++i) {
        for (int j = i + 1; j <= m_fixed; ++j) {
            if (target_adj[i][j] && !created_adj[i][j]) {
                missing_adj++;
            }
            if (!target_adj[i][j] && created_adj[i][j]) {
                extra_adj++;
            }
        }
    }

    return missing_adj * 100 + extra_adj;
}

void solve() {
    Timer timer;
    cin >> n_fixed >> m_fixed;
    for (int i = 0; i < n_fixed; ++i) {
        for (int j = 0; j < n_fixed; ++j) {
            cin >> initial_grid[i][j];
        }
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int i = 0; i < n_fixed; ++i) {
        for (int j = 0; j < n_fixed; ++j) {
            int c1 = initial_grid[i][j];
            if (i == 0 || i == n_fixed - 1 || j == 0 || j == n_fixed - 1) {
                target_adj[c1][0] = target_adj[0][c1] = true;
                is_coastal[c1] = true;
            }
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (ni >= 0 && ni < n_fixed && nj >= 0 && nj < n_fixed) {
                    int c2 = initial_grid[ni][nj];
                    if (c1 != c2) {
                        target_adj[c1][c2] = target_adj[c2][c1] = true;
                    }
                }
            }
        }
    }

    State current_state, best_state;
    vector<pair<int, int>> all_cells;
    for(int i=0; i<n_fixed; ++i) for(int j=0; j<n_fixed; ++j) all_cells.push_back({i,j});
    shuffle(all_cells.begin(), all_cells.end(), rng);
    
    vector<bool> used_cells_init(n_fixed*n_fixed, false);
    map<pair<int,int>, bool> pos_occupied;
    int cell_idx = 0;
    for(int k=1; k<=m_fixed; ++k){
        current_state.pos[k] = all_cells[cell_idx++];
        pos_occupied[current_state.pos[k]] = true;
    }

    current_state.score = calculate_energy(current_state);
    best_state = current_state;

    double start_temp = 50, end_temp = 0.1;
    long long time_limit = 2800;
    
    while (timer.get_ms() < time_limit) {
        double temp = start_temp + (end_temp - start_temp) * timer.get_ms() / time_limit;

        State next_state = current_state;
        int k1 = uniform_int_distribution<int>(1, m_fixed)(rng);
        
        if (uniform_int_distribution<int>(0, 1)(rng) == 0) {
            int k2 = uniform_int_distribution<int>(1, m_fixed)(rng);
            while(k1 == k2) k2 = uniform_int_distribution<int>(1, m_fixed)(rng);
            swap(next_state.pos[k1], next_state.pos[k2]);
        } else {
            pair<int, int> old_pos = next_state.pos[k1];
            
            pair<int, int> new_pos;
            do {
                new_pos = {uniform_int_distribution<int>(0, n_fixed - 1)(rng), uniform_int_distribution<int>(0, n_fixed - 1)(rng)};
            } while (pos_occupied.count(new_pos));
            next_state.pos[k1] = new_pos;
            pos_occupied.erase(old_pos);
            pos_occupied[new_pos] = true;
        }

        next_state.score = calculate_energy(next_state);

        double prob = exp((current_state.score - next_state.score) / temp);
        if (uniform_real_distribution<double>(0.0, 1.0)(rng) < prob) {
            current_state = next_state;
        } else {
            if (next_state.pos != current_state.pos) { // Revert pos_occupied if move rejected
                int k2 = -1; // find which positions were swapped
                for(int i=1; i<=m_fixed; ++i) {
                    if (i != k1 && next_state.pos[i] != current_state.pos[i]) {
                        k2 = i;
                        break;
                    }
                }
                if (k2 != -1) { // was a swap
                    // no change in pos_occupied
                } else { // was a move
                    pos_occupied.erase(next_state.pos[k1]);
                    pos_occupied[current_state.pos[k1]] = true;
                }
            }
        }
        if (current_state.score < best_state.score) {
            best_state = current_state;
        }
        if (best_state.score == 0) {
            break;
        }
    }

    vector<vector<int>> final_grid(n_fixed, vector<int>(n_fixed, 0));
    vector<vector<pair<int,int>>> regions(m_fixed + 1);
    for (int k = 1; k <= m_fixed; ++k) {
        final_grid[best_state.pos[k].first][best_state.pos[k].second] = k;
        regions[k].push_back(best_state.pos[k]);
    }

    bool satisfied_adj[M + 1][M + 1] = {};
    vector<vector<int>> dists(m_fixed + 1, vector<int>(n_fixed * n_fixed, -1));
    
    auto to_idx = [&](int r, int c){ return r * n_fixed + c; };

    for (int k = 1; k <= m_fixed; ++k) {
        queue<pair<int,int>> q;
        q.push(best_state.pos[k]);
        dists[k][to_idx(best_state.pos[k].first, best_state.pos[k].second)] = 0;
        int head = 0;
        vector<pair<int,int>> q_vec;
        q_vec.push_back(best_state.pos[k]);
        
        while(head < q_vec.size()){
            auto curr = q_vec[head++];
            int r = curr.first, c = curr.second;
            int d = dists[k][to_idx(r,c)];
            for(int i=0; i<4; ++i){
                int nr = r + dr[i], nc = c + dc[i];
                if(nr >= 0 && nr < n_fixed && nc >= 0 && nc < n_fixed && dists[k][to_idx(nr, nc)] == -1){
                    dists[k][to_idx(nr, nc)] = d + 1;
                    q_vec.push_back({nr, nc});
                }
            }
        }
    }
    
    int num_required_adj = 0;
    int num_satisfied_adj = 0;
    for(int i=0; i<=m_fixed; ++i) for(int j=i+1; j<=m_fixed; ++j) if(target_adj[i][j]) num_required_adj++;
    
    for (int iter_growth = 0; iter_growth < n_fixed * n_fixed && num_satisfied_adj < num_required_adj; ++iter_growth) {
        vector<tuple<double, int, pair<int, int>>> proposals;
        for (int k = 1; k <= m_fixed; ++k) {
            pair<int, int> best_cell = {-1, -1};
            double max_score = -1e18;

            for (auto& cell : regions[k]) {
                int r = cell.first, c = cell.second;
                for (int i = 0; i < 4; ++i) {
                    int nr = r + dr[i];
                    int nc = c + dc[i];

                    if (nr < 0 || nr >= n_fixed || nc < 0 || nc >= n_fixed || final_grid[nr][nc] != 0) continue;
                    
                    bool is_safe = true;
                    for (int j = 0; j < 4; ++j) {
                        int nnr = nr + dr[j], nnc = nc + dc[j];
                        if (nnr >= 0 && nnr < n_fixed && nnc >= 0 && nnc < n_fixed) {
                            int neighbor_color = final_grid[nnr][nnc];
                            if (neighbor_color != 0 && neighbor_color != k && !target_adj[k][neighbor_color]) {
                                is_safe = false; break;
                            }
                        }
                    }
                    if(!is_safe) continue;
                    if (nr == 0 || nr == n_fixed - 1 || nc == 0 || nc == n_fixed - 1) {
                        if (!target_adj[k][0]) is_safe = false;
                    }
                    if (!is_safe) continue;
                    
                    vector<pair<int, int>> zero_neighbors;
                    for (int j = 0; j < 4; ++j) {
                        int nnr = nr + dr[j], nnc = nc + dc[j];
                        if (nnr >= 0 && nnr < n_fixed && nnc >= 0 && nnc < n_fixed && final_grid[nnr][nnc] == 0) {
                            zero_neighbors.push_back({nnr, nnc});
                        }
                    }

                    if (zero_neighbors.size() > 1) {
                        final_grid[nr][nc] = k;
                        queue<pair<int,int>> q_check;
                        q_check.push(zero_neighbors[0]);
                        set<pair<int,int>> visited_check;
                        visited_check.insert(zero_neighbors[0]);
                        int reached_count = 1;
                        while(!q_check.empty()){
                            auto curr_check = q_check.front(); q_check.pop();
                            for(int j=0; j<4; ++j){
                                int r_check = curr_check.first + dr[j], c_check = curr_check.second + dc[j];
                                if(r_check >= 0 && r_check < n_fixed && c_check >= 0 && c_check < n_fixed && final_grid[r_check][c_check]==0 && visited_check.find({r_check, c_check}) == visited_check.end()){
                                    visited_check.insert({r_check, c_check});
                                    q_check.push({r_check, c_check});
                                }
                            }
                        }
                        for(size_t l=1; l < zero_neighbors.size(); ++l) {
                            if (visited_check.count(zero_neighbors[l])) reached_count++;
                        }
                        final_grid[nr][nc] = 0;
                        if (reached_count != zero_neighbors.size()) is_safe = false;
                    }
                    if(!is_safe) continue;

                    double current_score = rng();
                    for (int j = 0; j <= m_fixed; ++j) {
                        if (k != j && target_adj[k][j] && !satisfied_adj[k][j]) {
                            if (j == 0) {
                                current_score += 1e9 / (min({nr, nc, n_fixed-1-nr, n_fixed-1-nc}) + 1);
                            } else if (!regions[j].empty()) {
                                current_score += 1e9 / (dists[j][to_idx(nr, nc)] + 1);
                            }
                        }
                    }
                    if (current_score > max_score) {
                        max_score = current_score;
                        best_cell = {nr, nc};
                    }
                }
            }
            if (best_cell.first != -1) {
                proposals.emplace_back(max_score, k, best_cell);
            }
        }
        
        sort(proposals.rbegin(), proposals.rend());
        vector<bool> cell_taken(n_fixed * n_fixed, false);
        for(const auto& p : proposals){
            int k = get<1>(p);
            pair<int, int> cell = get<2>(p);
            if(cell_taken[to_idx(cell.first, cell.second)]) continue;
            if(final_grid[cell.first][cell.second] != 0) continue;

            final_grid[cell.first][cell.second] = k;
            regions[k].push_back(cell);
            cell_taken[to_idx(cell.first, cell.second)] = true;

            int d_cell = dists[k][to_idx(cell.first, cell.second)];
            if(d_cell == -1 || d_cell > 0) {
                // This shouldn't happen if logic is perfect, but as a safeguard.
                // A new cell must be adjacent to an existing cell of same color.
            }

            if (cell.first == 0 || cell.first == n_fixed - 1 || cell.second == 0 || cell.second == n_fixed - 1) {
                if(target_adj[k][0] && !satisfied_adj[k][0]){
                    satisfied_adj[k][0] = satisfied_adj[0][k] = true;
                    num_satisfied_adj++;
                }
            }
            for(int i=0; i<4; ++i){
                int nr = cell.first+dr[i], nc = cell.second+dc[i];
                if(nr >= 0 && nr < n_fixed && nc >= 0 && nc < n_fixed && final_grid[nr][nc] != 0){
                    int neighbor_color = final_grid[nr][nc];
                    if(target_adj[k][neighbor_color] && !satisfied_adj[k][neighbor_color]){
                        satisfied_adj[k][neighbor_color] = satisfied_adj[neighbor_color][k] = true;
                        num_satisfied_adj++;
                    }
                }
            }
        }
    }

    for (int i = 0; i < n_fixed; ++i) {
        for (int j = 0; j < n_fixed; ++j) {
            cout << final_grid[i][j] << (j == n_fixed - 1 ? "" : " ");
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}