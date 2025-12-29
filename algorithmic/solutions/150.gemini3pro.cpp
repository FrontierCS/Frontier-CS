#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cmath>
#include <cstring>
#include <random>
#include <chrono>

using namespace std;

const int N = 20;
int M;
vector<string> S;

// Trie structure to efficiently check string matches
const int MAX_NODES = 12000;
int trie_child[MAX_NODES][8];
vector<int> trie_ids[MAX_NODES];
int nodes_cnt = 1;

void reset_trie() {
    nodes_cnt = 1;
    memset(trie_child, -1, sizeof(trie_child));
    for(int i=0; i<MAX_NODES; ++i) trie_ids[i].clear();
}

void insert_trie(const string& s, int id) {
    int u = 0;
    for (char c : s) {
        int v = c - 'A';
        if (trie_child[u][v] == -1) {
            trie_child[u][v] = nodes_cnt++;
        }
        u = trie_child[u][v];
    }
    trie_ids[u].push_back(id);
}

int grid[N][N];
int best_grid[N][N];
int match_count[1000];
int satisfied_count = 0;

inline int wrap(int x) {
    if (x >= N) return x - N;
    if (x < 0) return x + N;
    return x;
}

// Function to update match counts when a cell changes
// val: the character value at (r, c) used for calculation (could be old or new)
// delta: +1 to add matches, -1 to remove matches
void update_matches(int r, int c, int val, int delta) {
    if (val < 0) return; // '.' does not contribute matches
    
    // Check Horizontal matches passing through (r, c)
    for (int d = 0; d < 12; ++d) {
        int start_col = wrap(c - d);
        int u = 0;
        for (int k = 0; k < 12; ++k) {
            int curr_c = wrap(start_col + k);
            int char_code;
            if (curr_c == c && r == r) char_code = val;
            else char_code = grid[r][curr_c];
            
            if (char_code < 0) break;
            if (trie_child[u][char_code] == -1) break;
            u = trie_child[u][char_code];
            
            // If we have a match of length k+1, and it covers the offset d
            if (k >= d) {
                for (int id : trie_ids[u]) {
                    int old_cnt = match_count[id];
                    match_count[id] += delta;
                    if (old_cnt == 0 && match_count[id] > 0) satisfied_count++;
                    else if (old_cnt > 0 && match_count[id] == 0) satisfied_count--;
                }
            }
        }
    }
    
    // Check Vertical matches passing through (r, c)
    for (int d = 0; d < 12; ++d) {
        int start_row = wrap(r - d);
        int u = 0;
        for (int k = 0; k < 12; ++k) {
            int curr_r = wrap(start_row + k);
            int char_code;
            if (curr_r == r && c == c) char_code = val;
            else char_code = grid[curr_r][c];
            
            if (char_code < 0) break;
            if (trie_child[u][char_code] == -1) break;
            u = trie_child[u][char_code];
            
            if (k >= d) {
                for (int id : trie_ids[u]) {
                    int old_cnt = match_count[id];
                    match_count[id] += delta;
                    if (old_cnt == 0 && match_count[id] > 0) satisfied_count++;
                    else if (old_cnt > 0 && match_count[id] == 0) satisfied_count--;
                }
            }
        }
    }
}

int loss_counts[1000];
vector<int> affected_ids;

// Check if we can replace character at (r, c) with '.' without reducing satisfied count
bool can_remove(int r, int c) {
    int val = grid[r][c];
    if (val < 0) return true; 
    
    affected_ids.clear();
    
    // Horizontal
    for (int d = 0; d < 12; ++d) {
        int start_col = wrap(c - d);
        int u = 0;
        for (int k = 0; k < 12; ++k) {
            int curr_c = wrap(start_col + k);
            int char_code = grid[r][curr_c];
            if (char_code < 0) break;
            if (trie_child[u][char_code] == -1) break;
            u = trie_child[u][char_code];
            if (k >= d) {
                for (int id : trie_ids[u]) {
                    if (loss_counts[id] == 0) affected_ids.push_back(id);
                    loss_counts[id]++;
                }
            }
        }
    }
    
    // Vertical
    for (int d = 0; d < 12; ++d) {
        int start_row = wrap(r - d);
        int u = 0;
        for (int k = 0; k < 12; ++k) {
            int curr_r = wrap(start_row + k);
            int char_code = grid[curr_r][c];
            if (char_code < 0) break;
            if (trie_child[u][char_code] == -1) break;
            u = trie_child[u][char_code];
            if (k >= d) {
                for (int id : trie_ids[u]) {
                    if (loss_counts[id] == 0) affected_ids.push_back(id);
                    loss_counts[id]++;
                }
            }
        }
    }
    
    bool possible = true;
    for (int id : affected_ids) {
        if (match_count[id] - loss_counts[id] <= 0) {
            possible = false;
        }
        loss_counts[id] = 0; 
    }
    
    return possible;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n_in;
    if (!(cin >> n_in >> M)) return 0;
    
    S.resize(M);
    for(int i=0; i<M; ++i) cin >> S[i];
    
    reset_trie();
    for(int i=0; i<M; ++i) insert_trie(S[i], i);
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    for(int i=0; i<N; ++i)
        for(int j=0; j<N; ++j)
            grid[i][j] = rng() % 8;
            
    memset(match_count, 0, sizeof(match_count));
    satisfied_count = 0;
    
    // Initial calculation of matches
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            // Horizontal
            int u = 0;
            for(int k=0; k<12; ++k) {
                int char_code = grid[i][wrap(j+k)];
                if (trie_child[u][char_code] == -1) break;
                u = trie_child[u][char_code];
                for(int id : trie_ids[u]) match_count[id]++;
            }
            // Vertical
            u = 0;
            for(int k=0; k<12; ++k) {
                int char_code = grid[wrap(i+k)][j];
                if (trie_child[u][char_code] == -1) break;
                u = trie_child[u][char_code];
                for(int id : trie_ids[u]) match_count[id]++;
            }
        }
    }
    
    for(int i=0; i<M; ++i) if(match_count[i] > 0) satisfied_count++;
    
    memcpy(best_grid, grid, sizeof(grid));
    int best_satisfied = satisfied_count;
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95;
    
    long long iter = 0;
    while(true) {
        iter++;
        if ((iter & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            if (chrono::duration<double>(curr_time - start_time).count() > time_limit) break;
        }
        
        int r = rng() % N;
        int c = rng() % N;
        int old_val = grid[r][c];
        int new_val = rng() % 8;
        if (new_val == old_val) new_val = (new_val + 1) % 8;
        
        int prev_satisfied = satisfied_count;
        
        // Try update: Remove old, Add new
        update_matches(r, c, old_val, -1);
        update_matches(r, c, new_val, 1);
        
        int delta = satisfied_count - prev_satisfied;
        
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
            double temp = 2.0 * (1.0 - elapsed / time_limit);
            if (temp > 1e-9) {
                double prob = exp(delta / temp);
                if (generate_canonical<double, 10>(rng) < prob) accept = true;
            }
        }
        
        if (accept) {
            grid[r][c] = new_val;
            if (satisfied_count > best_satisfied) {
                best_satisfied = satisfied_count;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            // Rollback
            update_matches(r, c, new_val, -1);
            update_matches(r, c, old_val, 1);
        }
    }
    
    // Post process
    memcpy(grid, best_grid, sizeof(grid));
    // Recalculate matches for safety
    memset(match_count, 0, sizeof(match_count));
    satisfied_count = 0;
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            int u = 0;
            for(int k=0; k<12; ++k) {
                int char_code = grid[i][wrap(j+k)];
                if (char_code < 0) break;
                if (trie_child[u][char_code] == -1) break;
                u = trie_child[u][char_code];
                for(int id : trie_ids[u]) match_count[id]++;
            }
            u = 0;
            for(int k=0; k<12; ++k) {
                int char_code = grid[wrap(i+k)][j];
                if (char_code < 0) break;
                if (trie_child[u][char_code] == -1) break;
                u = trie_child[u][char_code];
                for(int id : trie_ids[u]) match_count[id]++;
            }
        }
    }
    for(int i=0; i<M; ++i) if(match_count[i] > 0) satisfied_count++;
    
    // If all strings are satisfied, try to replace unnecessary chars with '.'
    if (satisfied_count == M) {
        bool changed = true;
        while(changed) {
            changed = false;
            for(int i=0; i<N; ++i) {
                for(int j=0; j<N; ++j) {
                    if (grid[i][j] != -1) {
                        if (can_remove(i, j)) {
                            int old_val = grid[i][j];
                            grid[i][j] = -1;
                            update_matches(i, j, old_val, -1);
                            changed = true;
                        }
                    }
                }
            }
        }
    }
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if (grid[i][j] == -1) cout << '.';
            else cout << (char)('A' + grid[i][j]);
        }
        cout << "\n";
    }
    
    return 0;
}