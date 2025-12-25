#include <bits/stdc++.h>
using namespace std;

const int N = 20;
int M;
vector<string> strs;
vector<int> lens;

// For incremental updates
struct Placement {
    int sid;
    int len;
    int matched;   // number of cells that currently match
};
vector<Placement> placements;
vector<vector<vector<pair<int, char>>>> cell_placements; // [N][N] -> (pid, required_char)

vector<int> match_count; // per string: number of matching placements
int covered;             // number of strings with match_count > 0

vector<vector<char>> mat; // current matrix

// Precompute all possible placements (horizontal and vertical) for every string.
void precompute_placements() {
    placements.clear();
    cell_placements.assign(N, vector<vector<pair<int, char>>>(N));
    for (int sid = 0; sid < M; ++sid) {
        int k = lens[sid];
        const string &s = strs[sid];
        // horizontal placements
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                int pid = placements.size();
                placements.push_back({sid, k, 0});
                for (int t = 0; t < k; ++t) {
                    int ci = i;
                    int cj = (j + t) % N;
                    cell_placements[ci][cj].push_back({pid, s[t]});
                }
            }
        }
        // vertical placements
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                int pid = placements.size();
                placements.push_back({sid, k, 0});
                for (int t = 0; t < k; ++t) {
                    int ci = (i + t) % N;
                    int cj = j;
                    cell_placements[ci][cj].push_back({pid, s[t]});
                }
            }
        }
    }
}

// Initialize matched counts and match_count from the current matrix.
void initialize_match_counts() {
    for (auto &pl : placements) pl.matched = 0;
    match_count.assign(M, 0);
    // count matches per placement
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char ch = mat[i][j];
            for (auto &p : cell_placements[i][j]) {
                int pid = p.first;
                char req = p.second;
                if (ch == req) placements[pid].matched++;
            }
        }
    }
    // compute match_count
    for (auto &pl : placements) {
        if (pl.matched == pl.len) match_count[pl.sid]++;
    }
    covered = 0;
    for (int sid = 0; sid < M; ++sid)
        if (match_count[sid] > 0) covered++;
}

// Information returned by the placement finder.
struct PlacementInfo {
    int orient;      // 0: horizontal, 1: vertical
    int start_i, start_j;
    int overlap;     // number of already filled cells that match
};

// Find the placement for string sid that is compatible with the current matrix
// and has the maximum overlap (already filled matching cells).
PlacementInfo find_best_placement(int sid, const vector<vector<char>> &cur_mat) {
    int k = lens[sid];
    const string &s = strs[sid];
    PlacementInfo best;
    best.overlap = -1;
    for (int orient = 0; orient < 2; ++orient) {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                bool compat = true;
                int overlap = 0;
                for (int t = 0; t < k; ++t) {
                    int ci, cj;
                    if (orient == 0) { ci = i; cj = (j + t) % N; }
                    else { ci = (i + t) % N; cj = j; }
                    char cell = cur_mat[ci][cj];
                    if (cell != '.') {
                        if (cell != s[t]) { compat = false; break; }
                        else ++overlap;
                    }
                }
                if (compat && overlap > best.overlap) {
                    best.orient = orient;
                    best.start_i = i;
                    best.start_j = j;
                    best.overlap = overlap;
                }
            }
        }
    }
    return best;
}

// Compute the number of strings covered by a given matrix (brute force).
int compute_coverage(const vector<vector<char>> &cur_mat) {
    int cnt = 0;
    for (int sid = 0; sid < M; ++sid) {
        int k = lens[sid];
        const string &s = strs[sid];
        bool ok = false;
        for (int orient = 0; orient < 2 && !ok; ++orient) {
            for (int i = 0; i < N && !ok; ++i) {
                for (int j = 0; j < N && !ok; ++j) {
                    bool match = true;
                    for (int t = 0; t < k; ++t) {
                        int ci, cj;
                        if (orient == 0) { ci = i; cj = (j + t) % N; }
                        else { ci = (i + t) % N; cj = j; }
                        if (cur_mat[ci][cj] != s[t]) { match = false; break; }
                    }
                    if (match) ok = true;
                }
            }
        }
        if (ok) cnt++;
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> N >> M;
    strs.resize(M);
    lens.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> strs[i];
        lens[i] = strs[i].size();
    }
    
    // random seed
    srand(time(0));
    
    // ---- Greedy placement with multiple trials ----
    const int TRIALS = 5;
    vector<vector<char>> best_mat;
    int best_cov = -1;
    
    for (int trial = 0; trial < TRIALS; ++trial) {
        vector<vector<char>> cur_mat(N, vector<char>(N, '.'));
        // order strings by length descending, random within same length
        vector<int> order(M);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (lens[a] != lens[b]) return lens[a] > lens[b];
            return rand() % 2;
        });
        
        // place strings greedily
        for (int idx : order) {
            PlacementInfo info = find_best_placement(idx, cur_mat);
            if (info.overlap >= 0) {
                int k = lens[idx];
                const string &s = strs[idx];
                for (int t = 0; t < k; ++t) {
                    int ci, cj;
                    if (info.orient == 0) { ci = info.start_i; cj = (info.start_j + t) % N; }
                    else { ci = (info.start_i + t) % N; cj = info.start_j; }
                    cur_mat[ci][cj] = s[t];
                }
            }
        }
        
        // fill remaining dots randomly
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (cur_mat[i][j] == '.')
                    cur_mat[i][j] = 'A' + (rand() % 8);
            }
        }
        
        int cov = compute_coverage(cur_mat);
        if (cov > best_cov) {
            best_cov = cov;
            best_mat = cur_mat;
        }
    }
    
    mat = best_mat;
    
    // ---- Precompute data structures for incremental updates ----
    precompute_placements();
    initialize_match_counts();
    
    // ---- Simulated Annealing to improve coverage ----
    const int ITER = 50000;
    double T = 1.0;
    double decay = 0.9999;   // cooling factor
    
    for (int iter = 0; iter < ITER; ++iter) {
        // pick a random cell and a new random character (different from current)
        int i = rand() % N;
        int j = rand() % N;
        char old_char = mat[i][j];
        char new_char;
        do {
            new_char = 'A' + (rand() % 8);
        } while (new_char == old_char);
        
        // compute delta in coverage
        int delta_c = 0;
        vector<pair<int, int>> pid_deltas;          // (pid, delta) for matched counts
        vector<int> sid_deltas(M, 0);               // change in match_count per string
        
        for (auto &p : cell_placements[i][j]) {
            int pid = p.first;
            char req = p.second;
            bool before = (old_char == req);
            bool after = (new_char == req);
            if (before == after) continue;
            int delta = after ? 1 : -1;
            int old_matched = placements[pid].matched;
            int new_matched = old_matched + delta;
            bool old_full = (old_matched == placements[pid].len);
            bool new_full = (new_matched == placements[pid].len);
            if (!old_full && new_full)
                sid_deltas[placements[pid].sid] += 1;
            else if (old_full && !new_full)
                sid_deltas[placements[pid].sid] -= 1;
            pid_deltas.push_back({pid, delta});
        }
        
        for (int sid = 0; sid < M; ++sid) {
            if (sid_deltas[sid] == 0) continue;
            int old_cnt = match_count[sid];
            int new_cnt = old_cnt + sid_deltas[sid];
            if (old_cnt == 0 && new_cnt > 0) delta_c++;
            else if (old_cnt > 0 && new_cnt == 0) delta_c--;
        }
        
        // accept or reject
        bool accept = false;
        if (delta_c > 0) accept = true;
        else {
            double prob = exp(delta_c / T);
            double r = rand() / (RAND_MAX + 1.0);
            if (r < prob) accept = true;
        }
        
        if (accept) {
            // apply changes
            for (auto &p : pid_deltas)
                placements[p.first].matched += p.second;
            for (int sid = 0; sid < M; ++sid)
                if (sid_deltas[sid] != 0)
                    match_count[sid] += sid_deltas[sid];
            mat[i][j] = new_char;
            covered += delta_c;
        }
        
        T *= decay;
    }
    
    // ---- Output final matrix ----
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j)
            cout << mat[i][j];
        cout << '\n';
    }
    
    return 0;
}