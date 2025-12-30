#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>
#include <cmath>

using namespace std;

// Constants
const int N = 20;
const int MAX_M = 805;
const int MAX_LEN = 15;
const int MAX_NODES = 15000;
const double TIME_LIMIT = 1.95;

// Random number generator (Xorshift)
struct Xorshift {
    uint32_t x, y, z, w;
    Xorshift(uint32_t seed = 123456789) {
        x = seed; y = 362436069; z = 521288629; w = 88675123;
    }
    uint32_t next() {
        uint32_t t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    int next_int(int n) {
        return next() % n;
    }
    double next_double() {
        return (double)next() / 0xFFFFFFFF;
    }
} rng;

// Timer
struct Timer {
    chrono::high_resolution_clock::time_point start;
    Timer() { reset(); }
    void reset() { start = chrono::high_resolution_clock::now(); }
    double elapsed() {
        auto end = chrono::high_resolution_clock::now();
        return chrono::duration<double>(end - start).count();
    }
} timer;

// Global Data
int M;
vector<string> S;
int lens[MAX_M];
char grid[N][N];
int max_len = 0;

// Aho-Corasick Automaton
struct AhoCorasick {
    int trie[MAX_NODES][8];
    int fail[MAX_NODES];
    vector<int> outputs[MAX_NODES]; 
    int nodes_cnt = 1;

    AhoCorasick() {
        memset(trie, -1, sizeof(trie));
        memset(fail, 0, sizeof(fail));
    }

    void insert(const string& s, int id) {
        int u = 0;
        for (char c : s) {
            int digit = c - 'A';
            if (trie[u][digit] == -1) {
                memset(trie[nodes_cnt], -1, sizeof(trie[nodes_cnt]));
                outputs[nodes_cnt].clear();
                trie[u][digit] = nodes_cnt++;
            }
            u = trie[u][digit];
        }
        outputs[u].push_back(id);
    }

    void build() {
        queue<int> q;
        for (int i = 0; i < 8; ++i) {
            if (trie[0][i] != -1) {
                fail[trie[0][i]] = 0;
                q.push(trie[0][i]);
            } else {
                trie[0][i] = 0;
            }
        }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (fail[u] != 0) {
                outputs[u].insert(outputs[u].end(), outputs[fail[u]].begin(), outputs[fail[u]].end());
            }
            for (int i = 0; i < 8; ++i) {
                if (trie[u][i] != -1) {
                    fail[trie[u][i]] = trie[fail[u]][i];
                    q.push(trie[u][i]);
                } else {
                    trie[u][i] = trie[fail[u]][i];
                }
            }
        }
    }
} ac;

// State Data
int string_counts[MAX_M];
int matched_count = 0;

// Optimized list to store matches per row/col
struct MatchList {
    int ids[300]; 
    int size = 0;
    void clear() { size = 0; }
    void add(int id) { if(size < 300) ids[size++] = id; }
} row_matches[N], col_matches[N];

void get_matches_for_row(int r, MatchList& ml) {
    ml.clear();
    int seq[N + MAX_LEN];
    for(int i=0; i<N; ++i) seq[i] = grid[r][i] - 'A';
    for(int i=0; i<max_len-1; ++i) seq[N+i] = seq[i];
    
    int u = 0;
    int limit = N + max_len - 1;
    for (int i = 0; i < limit; ++i) {
        int val = seq[i];
        if (val < 0 || val >= 8) {
            u = 0; 
            continue;
        }
        u = ac.trie[u][val];
        for (int id : ac.outputs[u]) {
            int len = lens[id];
            int start = i - len + 1;
            if (start >= 0 && start < N) {
                ml.add(id);
            }
        }
    }
}

void get_matches_for_col(int c, MatchList& ml) {
    ml.clear();
    int seq[N + MAX_LEN];
    for(int i=0; i<N; ++i) seq[i] = grid[i][c] - 'A';
    for(int i=0; i<max_len-1; ++i) seq[N+i] = seq[i];
    
    int u = 0;
    int limit = N + max_len - 1;
    for (int i = 0; i < limit; ++i) {
        int val = seq[i];
        if (val < 0 || val >= 8) {
            u = 0;
            continue;
        }
        u = ac.trie[u][val];
        for (int id : ac.outputs[u]) {
            int len = lens[id];
            int start = i - len + 1;
            if (start >= 0 && start < N) {
                ml.add(id);
            }
        }
    }
}

void compute_full_score() {
    memset(string_counts, 0, sizeof(string_counts));
    matched_count = 0;
    for(int r=0; r<N; ++r) {
        get_matches_for_row(r, row_matches[r]);
        for(int i=0; i<row_matches[r].size; ++i) string_counts[row_matches[r].ids[i]]++;
    }
    for(int c=0; c<N; ++c) {
        get_matches_for_col(c, col_matches[c]);
        for(int i=0; i<col_matches[c].size; ++i) string_counts[col_matches[c].ids[i]]++;
    }
    for(int i=0; i<M; ++i) if(string_counts[i] > 0) matched_count++;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    S.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> S[i];
        lens[i] = S[i].length();
        max_len = max(max_len, lens[i]);
        ac.insert(S[i], i);
    }
    ac.build();

    // Initial random fill
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) grid[i][j] = '.';
    
    // Heuristic Initialization: Scatter strings
    vector<int> p(M);
    for(int i=0; i<M; ++i) p[i] = i;
    for(int i=M-1; i>0; --i) swap(p[i], p[rng.next_int(i+1)]);
    
    for(int k : p) {
        int r = rng.next_int(N);
        int c = rng.next_int(N);
        int dir = rng.next_int(2);
        for(int i=0; i<lens[k]; ++i) {
            if(dir == 0) grid[r][(c+i)%N] = S[k][i];
            else grid[(r+i)%N][c] = S[k][i];
        }
    }
    // Fill gaps
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if(grid[i][j] == '.') grid[i][j] = 'A' + rng.next_int(8);
        }
    }

    compute_full_score();
    
    // Simulated Annealing
    double start_temp = 2.0;
    double end_temp = 0.0;
    int current_score = matched_count;
    
    MatchList old_row_ml, old_col_ml;
    MatchList new_row_ml, new_col_ml;
    
    long long iter = 0;
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            if (timer.elapsed() > TIME_LIMIT) break;
        }

        double el = timer.elapsed();
        double temp = start_temp + (end_temp - start_temp) * (el / TIME_LIMIT);

        int r = rng.next_int(N);
        int c = rng.next_int(N);
        char old_char = grid[r][c];
        char new_char = 'A' + rng.next_int(8);
        if (new_char == old_char) continue;

        old_row_ml = row_matches[r];
        old_col_ml = col_matches[c];

        int next_matched_count = matched_count;
        
        // Remove contribution of current row/col matches
        for(int i=0; i<old_row_ml.size; ++i) {
            int id = old_row_ml.ids[i];
            string_counts[id]--;
            if(string_counts[id] == 0) next_matched_count--;
        }
        for(int i=0; i<old_col_ml.size; ++i) {
            int id = old_col_ml.ids[i];
            string_counts[id]--;
            if(string_counts[id] == 0) next_matched_count--;
        }

        // Apply change
        grid[r][c] = new_char;

        // Calculate new matches
        get_matches_for_row(r, new_row_ml);
        get_matches_for_col(c, new_col_ml);

        // Add contribution
        for(int i=0; i<new_row_ml.size; ++i) {
            int id = new_row_ml.ids[i];
            if(string_counts[id] == 0) next_matched_count++;
            string_counts[id]++;
        }
        for(int i=0; i<new_col_ml.size; ++i) {
            int id = new_col_ml.ids[i];
            if(string_counts[id] == 0) next_matched_count++;
            string_counts[id]++;
        }
        
        // Accept or Reject
        int delta = next_matched_count - current_score;
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp(delta / temp);
            if (rng.next_double() < prob) accept = true;
        }

        if (accept) {
            current_score = next_matched_count;
            row_matches[r] = new_row_ml; 
            col_matches[c] = new_col_ml;
            matched_count = next_matched_count; 
        } else {
            // Revert changes to counts
            for(int i=0; i<new_row_ml.size; ++i) {
                int id = new_row_ml.ids[i];
                string_counts[id]--;
            }
             for(int i=0; i<new_col_ml.size; ++i) {
                int id = new_col_ml.ids[i];
                string_counts[id]--;
            }
            
            for(int i=0; i<old_row_ml.size; ++i) {
                int id = old_row_ml.ids[i];
                string_counts[id]++;
            }
            for(int i=0; i<old_col_ml.size; ++i) {
                int id = old_col_ml.ids[i];
                string_counts[id]++;
            }
            
            grid[r][c] = old_char;
        }
    }

    // Post-processing: try to replace chars with '.' if we have perfect match
    if (matched_count == M) {
        for(int r=0; r<N; ++r) {
            for(int c=0; c<N; ++c) {
                char original = grid[r][c];
                grid[r][c] = '.';
                
                MatchList old_r = row_matches[r];
                MatchList old_c = col_matches[c];
                
                // Fast check if possible
                bool possible = true;
                for(int i=0; i<old_r.size; ++i) {
                   if (string_counts[old_r.ids[i]] == 1) { possible = false; break; }
                }
                if (possible) {
                    for(int i=0; i<old_c.size; ++i) {
                       if (string_counts[old_c.ids[i]] == 1) { possible = false; break; }
                    }
                }

                if (possible) {
                    // Accurate check
                    for(int i=0; i<old_r.size; ++i) string_counts[old_r.ids[i]]--;
                    for(int i=0; i<old_c.size; ++i) string_counts[old_c.ids[i]]--;
                    
                    get_matches_for_row(r, new_row_ml); 
                    get_matches_for_col(c, new_col_ml);
                    
                    for(int i=0; i<new_row_ml.size; ++i) string_counts[new_row_ml.ids[i]]++;
                    for(int i=0; i<new_col_ml.size; ++i) string_counts[new_col_ml.ids[i]]++;
                    
                    bool ok = true;
                    for(int i=0; i<M; ++i) if(string_counts[i] == 0) { ok = false; break; }
                    
                    if (!ok) {
                         // Revert
                         for(int i=0; i<new_row_ml.size; ++i) string_counts[new_row_ml.ids[i]]--;
                         for(int i=0; i<new_col_ml.size; ++i) string_counts[new_col_ml.ids[i]]--;
                         
                         for(int i=0; i<old_r.size; ++i) string_counts[old_r.ids[i]]++;
                         for(int i=0; i<old_c.size; ++i) string_counts[old_c.ids[i]]++;
                         grid[r][c] = original;
                    } else {
                        // Accept '.'
                        row_matches[r] = new_row_ml;
                        col_matches[c] = new_col_ml;
                    }
                } else {
                     grid[r][c] = original;
                }
            }
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << grid[i][j];
        }
        cout << "\n";
    }

    return 0;
}