#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

// 128-bit integer to hold bitmasks for the 112 cells (8x14)
typedef unsigned __int128 u128;

const int R = 8;
const int C = 14;
const int N = R * C; // 112

// Global data structures
u128 adj[N];       // Adjacency masks for each cell
u128 pos[10];      // Masks for positions of each digit
int grid[N];       // The grid digits

// Initialize adjacency masks
void init_adj() {
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int u = r * C + c;
            adj[u] = 0;
            // Check all 8 neighbors
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr;
                    int nc = c + dc;
                    if (nr >= 0 && nr < R && nc >= 0 && nc < C) {
                        int v = nr * C + nc;
                        adj[u] |= ((u128)1 << v);
                    }
                }
            }
        }
    }
}

// Function to calculate the score: the largest X such that 1..X can be read
// Returns X.
inline int check() {
    int digits[20];
    for (int n = 1; ; ++n) {
        int temp = n;
        int len = 0;
        // Extract digits (reversed order, but we access from end)
        do {
            digits[len++] = temp % 10;
            temp /= 10;
        } while (temp);

        // Start with the set of positions for the first digit
        u128 mask = pos[digits[len - 1]];
        if (!mask) return n - 1;

        // For subsequent digits, compute reachable positions
        for (int i = len - 2; i >= 0; --i) {
            int d = digits[i];
            u128 next_mask = 0;
            u128 m = mask;
            
            // Expand current mask to all neighbors efficiently
            while (m) {
                unsigned long long low = (unsigned long long)m;
                if (low) {
                    int bit = __builtin_ctzll(low);
                    next_mask |= adj[bit];
                    m &= m - 1; // Clear LSB
                } else {
                    unsigned long long high = (unsigned long long)(m >> 64);
                    int bit = __builtin_ctzll(high);
                    next_mask |= adj[bit + 64];
                    m &= m - 1;
                }
            }
            
            // Intersect with positions of the next digit
            mask = next_mask & pos[d];
            if (!mask) return n - 1;
        }
    }
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::steady_clock::now();
    
    init_adj();
    
    // Seed with time
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist_digit(0, 9);
    uniform_int_distribution<int> dist_cell(0, N - 1);

    // Random initialization
    for (int i = 0; i < N; ++i) grid[i] = dist_digit(rng);
    
    // Initialize position masks based on grid
    for (int d = 0; d < 10; ++d) pos[d] = 0;
    for (int i = 0; i < N; ++i) pos[grid[i]] |= ((u128)1 << i);

    // Keep track of best solution
    int best_grid[N];
    memcpy(best_grid, grid, sizeof(grid));
    int best_score = check();
    int curr_score = best_score;

    // Hill climbing loop
    long long iter = 0;
    while (true) {
        iter++;
        // Check time limit roughly every 256 iterations
        if ((iter & 255) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > 58000) break;
        }

        // Mutate a random cell
        int cell = dist_cell(rng);
        int old_val = grid[cell];
        int new_val = dist_digit(rng);
        
        if (old_val == new_val) continue;

        // Apply mutation
        grid[cell] = new_val;
        pos[old_val] &= ~((u128)1 << cell);
        pos[new_val] |= ((u128)1 << cell);

        // Calculate new score
        int sc = check();

        // Acceptance criteria: Hill Climbing (accept if score >= current)
        // This allows sideways moves on plateaus
        if (sc >= curr_score) {
            curr_score = sc;
            if (sc > best_score) {
                best_score = sc;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            // Reject and revert
            grid[cell] = old_val;
            pos[new_val] &= ~((u128)1 << cell);
            pos[old_val] |= ((u128)1 << cell);
        }
    }

    // Print the best grid found
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << best_grid[r * C + c];
        }
        cout << "\n";
    }

    return 0;
}