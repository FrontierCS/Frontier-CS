#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <map>
#include <random>
#include <cstring>

using namespace std;

// Problem constants
const int N = 20;
const double TIME_LIMIT = 1.95;

// Random number generator
mt19937 rng(12345);

// Trie Structure to store unique strings
struct TrieNode {
    int next[8];
    int string_id; // ID of the unique string ending here, -1 if none
    TrieNode() {
        memset(next, -1, sizeof(next));
        string_id = -1;
    }
};

vector<TrieNode> trie;
// Insert a string into the trie
void insert_string(const string& s, int id) {
    int curr = 0;
    for (char c : s) {
        int d = c - 'A';
        if (trie[curr].next[d] == -1) {
            trie[curr].next[d] = trie.size();
            trie.push_back(TrieNode());
        }
        curr = trie[curr].next[d];
    }
    trie[curr].string_id = id;
}

// Global state
vector<string> unique_strings;
vector<int> weights; // Number of input strings corresponding to each unique string
vector<int> counts;  // How many times each unique string appears in the grid
int total_satisfied_weight = 0; // Current score
char grid[N][N];

// Helper for wrapping coordinates (torus)
inline int wrap(int x) {
    return (x % N + N) % N;
}

// Update the counts based on changing grid[r][c]
// delta: -1 to remove influence of 'ch', +1 to add influence of 'ch'
// We assume grid[r][c] conceptually holds 'ch' during this check
// Note: This function depends on grid[][] having valid chars for neighbors
void modify(int r, int c, char ch, int delta) {
    int val = ch - 'A';
    
    // Check horizontal subsequences passing through (r, c)
    // We check start positions such that the string covers column c
    for (int offset = 0; offset < 12; ++offset) {
        int start_col = wrap(c - offset);
        int node = 0;
        // Traverse trie
        for (int k = 0; k < 12; ++k) {
            int cur_col = wrap(start_col + k);
            int char_idx;
            // If we are at the modified cell, use the hypothetical char 'val'
            if (cur_col == c) char_idx = val;
            else char_idx = grid[r][cur_col] - 'A';
            
            if (trie[node].next[char_idx] == -1) break;
            node = trie[node].next[char_idx];
            
            // If a string ends here
            if (trie[node].string_id != -1) {
                // Check if the string actually overlaps (r, c)
                // Since we started 'offset' steps left of c, and current length is k+1,
                // we need offset <= k to ensure c is within [start_col, cur_col]
                if (offset <= k) {
                    int id = trie[node].string_id;
                    if (delta == -1) {
                        counts[id]--;
                        if (counts[id] == 0) total_satisfied_weight -= weights[id];
                    } else {
                        if (counts[id] == 0) total_satisfied_weight += weights[id];
                        counts[id]++;
                    }
                }
            }
        }
    }
    
    // Check vertical subsequences passing through (r, c)
    for (int offset = 0; offset < 12; ++offset) {
        int start_row = wrap(r - offset);
        int node = 0;
        for (int k = 0; k < 12; ++k) {
            int cur_row = wrap(start_row + k);
            int char_idx;
            if (cur_row == r) char_idx = val;
            else char_idx = grid[cur_row][c] - 'A';
            
            if (trie[node].next[char_idx] == -1) break;
            node = trie[node].next[char_idx];
            
            if (trie[node].string_id != -1) {
                if (offset <= k) {
                    int id = trie[node].string_id;
                    if (delta == -1) {
                        counts[id]--;
                        if (counts[id] == 0) total_satisfied_weight -= weights[id];
                    } else {
                        if (counts[id] == 0) total_satisfied_weight += weights[id];
                        counts[id]++;
                    }
                }
            }
        }
    }
}

// Recalculate everything from scratch (used for initialization)
void full_recalc() {
    fill(counts.begin(), counts.end(), 0);
    total_satisfied_weight = 0;
    
    // Horizontal
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int node = 0;
            for (int k = 0; k < 12; ++k) {
                int char_idx = grid[r][wrap(c + k)] - 'A';
                if (trie[node].next[char_idx] == -1) break;
                node = trie[node].next[char_idx];
                if (trie[node].string_id != -1) {
                    counts[trie[node].string_id]++;
                }
            }
        }
    }
    
    // Vertical
    for (int c = 0; c < N; ++c) {
        for (int r = 0; r < N; ++r) {
            int node = 0;
            for (int k = 0; k < 12; ++k) {
                int char_idx = grid[wrap(r + k)][c] - 'A';
                if (trie[node].next[char_idx] == -1) break;
                node = trie[node].next[char_idx];
                if (trie[node].string_id != -1) {
                    counts[trie[node].string_id]++;
                }
            }
        }
    }
    
    for (size_t i = 0; i < unique_strings.size(); ++i) {
        if (counts[i] > 0) total_satisfied_weight += weights[i];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int dummy_N, M;
    if (!(cin >> dummy_N >> M)) return 0;
    
    map<string, int> str_to_id;
    trie.push_back(TrieNode()); // Root
    
    for (int i = 0; i < M; ++i) {
        string s;
        cin >> s;
        if (str_to_id.find(s) == str_to_id.end()) {
            int id = unique_strings.size();
            str_to_id[s] = id;
            unique_strings.push_back(s);
            weights.push_back(0);
            insert_string(s, id);
        }
        weights[str_to_id[s]]++;
    }
    
    counts.resize(unique_strings.size(), 0);
    
    // Initialize grid randomly
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            grid[i][j] = 'A' + (rng() % 8);
        }
    }
    
    full_recalc();
    
    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double start_temp = 2.5;
    double end_temp = 0.0;
    double temp = start_temp;
    
    int best_score = total_satisfied_weight;
    char best_grid[N][N];
    memcpy(best_grid, grid, sizeof(grid));
    
    int iter = 0;
    while (true) {
        iter++;
        // Update temperature and check time periodically
        if ((iter & 1023) == 0) {
             double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
             if (elapsed > TIME_LIMIT) break;
             temp = start_temp + (end_temp - start_temp) * (elapsed / TIME_LIMIT);
        }

        // Propose a change
        int r = rng() % N;
        int c = rng() % N;
        char old_char = grid[r][c];
        char new_char = 'A' + (rng() % 8);
        if (old_char == new_char) continue;
        
        int prev_score = total_satisfied_weight;
        
        // Apply change temporarily
        // 1. Remove contribution of old_char
        modify(r, c, old_char, -1);
        // 2. Update grid
        grid[r][c] = new_char;
        // 3. Add contribution of new_char
        modify(r, c, new_char, 1);
        
        int new_score = total_satisfied_weight;
        int delta = new_score - prev_score;
        
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
             // Metropolis criterion
             if (generate_canonical<double, 10>(rng) < exp(delta / temp)) {
                 accept = true;
             }
        }
        
        if (accept) {
            if (new_score > best_score) {
                best_score = new_score;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            // Revert changes
            modify(r, c, new_char, -1);
            grid[r][c] = old_char;
            modify(r, c, old_char, 1);
        }
    }
    
    // Output result
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << best_grid[i][j];
        }
        cout << "\n";
    }

    return 0;
}