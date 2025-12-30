#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <unordered_map>
#include <algorithm>
#include <cstring>

using namespace std;

// ---------------------- Globals ----------------------
const int N = 20;
int M;
vector<string> S;
int counts_arr[1000]; // counts for each string
int satisfied_count = 0;
char grid[N][N];
const char CHARS[] = "ABCDEFGH";
typedef unsigned long long ULL;
ULL BASE = 1000000007; 

unordered_map<ULL, vector<int>> hash_to_ids;

// Random number generator
mt19937 rng(12345);

// ---------------------- Hashing ----------------------

void init_hash_map() {
    hash_to_ids.clear();
    for (int i = 0; i < M; ++i) {
        ULL h = 0;
        for (char c : S[i]) {
            h = h * BASE + (c - 'A' + 1); 
        }
        hash_to_ids[h].push_back(i);
    }
}

// ---------------------- Update Logic ----------------------

// Update contribution of cell (r, c)
// delta = -1 (remove) or +1 (add)
// Uses current grid[r][c] for calculation. 
inline void update_counts(int r, int c, int delta) {
    // Horizontal patterns
    for (int k = 0; k < 12; ++k) {
        int sc = (c - k + N) % N;
        ULL h = 0;
        for (int p = 0; p < 12; ++p) { 
            char ch = grid[r][(sc + p) % N];
            if (ch == '.') {
                h = h * BASE + 99; 
            } else {
                h = h * BASE + (ch - 'A' + 1);
            }
            
            if (p >= k) {
                 if (hash_to_ids.count(h)) {
                     const vector<int>& ids = hash_to_ids.at(h);
                     for (int id : ids) {
                         int old = counts_arr[id];
                         counts_arr[id] += delta;
                         if (old == 0 && counts_arr[id] > 0) satisfied_count++;
                         else if (old > 0 && counts_arr[id] == 0) satisfied_count--;
                     }
                 }
            }
        }
    }
    
    // Vertical patterns
    for (int k = 0; k < 12; ++k) {
        int sr = (r - k + N) % N;
        ULL h = 0;
        for (int p = 0; p < 12; ++p) {
            char ch = grid[(sr + p) % N][c];
            if (ch == '.') h = h * BASE + 99;
            else h = h * BASE + (ch - 'A' + 1);
            
            if (p >= k) {
                 if (hash_to_ids.count(h)) {
                     const vector<int>& ids = hash_to_ids.at(h);
                     for (int id : ids) {
                         int old = counts_arr[id];
                         counts_arr[id] += delta;
                         if (old == 0 && counts_arr[id] > 0) satisfied_count++;
                         else if (old > 0 && counts_arr[id] == 0) satisfied_count--;
                     }
                 }
            }
        }
    }
}

void full_recalc() {
    memset(counts_arr, 0, sizeof(counts_arr));
    satisfied_count = 0;
    
    // Horizontal
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            ULL h = 0;
            for (int len = 1; len <= 12; ++len) {
                char ch = grid[r][(c + len - 1) % N];
                if (ch == '.') h = h * BASE + 99;
                else h = h * BASE + (ch - 'A' + 1);
                
                if (hash_to_ids.count(h)) {
                    for (int id : hash_to_ids.at(h)) counts_arr[id]++;
                }
            }
        }
    }
    
    // Vertical
    for (int c = 0; c < N; ++c) {
        for (int r = 0; r < N; ++r) {
            ULL h = 0;
            for (int len = 1; len <= 12; ++len) {
                char ch = grid[(r + len - 1) % N][c];
                if (ch == '.') h = h * BASE + 99;
                else h = h * BASE + (ch - 'A' + 1);
                
                if (hash_to_ids.count(h)) {
                    for (int id : hash_to_ids.at(h)) counts_arr[id]++;
                }
            }
        }
    }
    
    for (int i = 0; i < M; ++i) {
        if (counts_arr[i] > 0) satisfied_count++;
    }
}

// ---------------------- Main Solver ----------------------

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int N_in;
    cin >> N_in >> M; 
    S.resize(M);
    for (int i = 0; i < M; ++i) cin >> S[i];
    
    ULL seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    rng.seed(seed);
    BASE = (seed % 10000) * 2 + 12345; 
    if (BASE % 2 == 0) BASE++;

    init_hash_map();
    
    // Init Grid Randomly
    uniform_int_distribution<int> dist8(0, 7);
    uniform_int_distribution<int> distN(0, N - 1);
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            grid[i][j] = CHARS[dist8(rng)];
        }
    }
    
    full_recalc();
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; 
    
    int best_satisfied = satisfied_count;
    char best_grid[N][N];
    memcpy(best_grid, grid, sizeof(grid));
    
    long long iter = 0;
    
    struct Backup {
        int r, c;
        char ch;
    } backups[15];
    
    uniform_real_distribution<double> dist01(0.0, 1.0);
    
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(curr_time - start_time).count();
            if (elapsed > time_limit) break;
        }
        
        bool try_string_force = false;
        // Prioritize force move if not solved
        if (satisfied_count < M && dist01(rng) < 0.4) {
            try_string_force = true;
        }
        
        if (try_string_force) {
            int start_idx = uniform_int_distribution<int>(0, M - 1)(rng);
            int target_s = -1;
            for (int k = 0; k < M; ++k) {
                int idx = (start_idx + k) % M;
                if (counts_arr[idx] == 0) {
                    target_s = idx;
                    break;
                }
            }
            
            if (target_s != -1) {
                const string& s = S[target_s];
                int len = s.length();
                int r = distN(rng);
                int c = distN(rng);
                int dir = uniform_int_distribution<int>(0, 1)(rng); 
                
                int current_score = satisfied_count;
                
                for (int k = 0; k < len; ++k) {
                    int rr, cc;
                    if (dir == 0) { rr = r; cc = (c + k) % N; }
                    else { rr = (r + k) % N; cc = c; }
                    
                    backups[k] = {rr, cc, grid[rr][cc]};
                    
                    if (grid[rr][cc] != s[k]) {
                        update_counts(rr, cc, -1);
                        grid[rr][cc] = s[k];
                        update_counts(rr, cc, 1);
                    }
                }
                
                if (satisfied_count >= current_score) {
                    if (satisfied_count > best_satisfied) {
                        best_satisfied = satisfied_count;
                        memcpy(best_grid, grid, sizeof(grid));
                    }
                } else {
                    for (int k = len - 1; k >= 0; --k) {
                        int rr = backups[k].r;
                        int cc = backups[k].c;
                        char old_ch = backups[k].ch;
                        if (grid[rr][cc] != old_ch) {
                            update_counts(rr, cc, -1);
                            grid[rr][cc] = old_ch;
                            update_counts(rr, cc, 1);
                        }
                    }
                }
                continue; 
            }
        }
        
        // Single cell flip
        int r = distN(rng);
        int c = distN(rng);
        char old_char = grid[r][c];
        char new_char = CHARS[dist8(rng)];
        if (new_char == old_char) continue;
        
        int prev_sat = satisfied_count;
        
        update_counts(r, c, -1);
        grid[r][c] = new_char;
        update_counts(r, c, 1);
        
        if (satisfied_count >= prev_sat) {
            if (satisfied_count > best_satisfied) {
                best_satisfied = satisfied_count;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            update_counts(r, c, -1);
            grid[r][c] = old_char;
            update_counts(r, c, 1);
        }
    }
    
    memcpy(grid, best_grid, sizeof(grid));
    full_recalc(); 
    
    // Dot Optimization
    if (satisfied_count == M) {
        vector<pair<int, int>> cells;
        for (int i=0; i<N; ++i) for(int j=0; j<N; ++j) cells.push_back({i, j});
        shuffle(cells.begin(), cells.end(), rng);
        
        for (auto p : cells) {
            int r = p.first;
            int c = p.second;
            char old_char = grid[r][c];
            if (old_char == '.') continue;
            
            update_counts(r, c, -1);
            grid[r][c] = '.';
            update_counts(r, c, 1);
            
            if (satisfied_count < M) {
                update_counts(r, c, -1);
                grid[r][c] = old_char;
                update_counts(r, c, 1);
            }
        }
    }
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << grid[i][j];
        }
        cout << "\n";
    }
    
    return 0;
}