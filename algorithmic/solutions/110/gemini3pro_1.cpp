#include <iostream>
#include <vector>
#include <string>
#include <ctime>
#include <cstring>
#include <cstdint>

using namespace std;

// Grid dimensions
const int R = 8;
const int C = 14;
const int N = R * C;

// Xorshift RNG for speed
struct Xorshift {
    uint32_t x = 123456789;
    uint32_t y = 362436069;
    uint32_t z = 521288629;
    uint32_t w = 88675123;
    uint32_t next() {
        uint32_t t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = w ^ (w >> 19) ^ t ^ (t >> 8);
    }
    int next_int(int n) {
        return next() % n;
    }
} rng;

// Bitset for 112 elements
// Uses two 64-bit integers to store 112 bits
struct Bitset {
    uint64_t v0, v1;
    
    Bitset() : v0(0), v1(0) {}
    
    inline void set(int bit) {
        if (bit < 64) v0 |= (1ULL << bit);
        else v1 |= (1ULL << (bit - 64));
    }
    
    inline bool empty() const {
        return (v0 | v1) == 0;
    }

    inline void ip_or(const Bitset& other) {
        v0 |= other.v0;
        v1 |= other.v1;
    }

    inline Bitset operator&(const Bitset& other) const {
        Bitset res;
        res.v0 = v0 & other.v0;
        res.v1 = v1 & other.v1;
        return res;
    }
};

Bitset adj[N];
Bitset digit_pos[10];
int grid_data[N];
int best_grid[N];

void init_adj() {
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};
    
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int u = r * C + c;
            for (int i = 0; i < 8; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (nr >= 0 && nr < R && nc >= 0 && nc < C) {
                    int v = nr * C + nc;
                    adj[u].set(v);
                }
            }
        }
    }
}

// Calculate score: max X such that 1..X are readable from the grid
// Uses bitmask DP/BFS simulation
int calc_score(int threshold) {
    int val = 1;
    char buf[16];
    
    while (true) {
        // Convert val to digits in buf (digits will be in reverse order: buf[0] is last digit)
        int len = 0;
        int temp = val;
        // val starts at 1, so temp > 0 initially
        while(temp > 0) {
            buf[len++] = (temp % 10);
            temp /= 10;
        }
        
        // Start check with the first digit of the number (which is at buf[len-1])
        int d = buf[len-1];
        Bitset mask = digit_pos[d];
        bool possible = !mask.empty();
        
        if (possible) {
            // Process subsequent digits
            for (int i = len - 2; i >= 0; --i) {
                Bitset next_mask;
                int next_d = buf[i];
                
                // Expand mask to neighbors
                uint64_t t0 = mask.v0;
                while (t0) {
                    int b = __builtin_ctzll(t0);
                    next_mask.ip_or(adj[b]);
                    t0 &= ~(1ULL << b);
                }
                uint64_t t1 = mask.v1;
                while (t1) {
                    int b = __builtin_ctzll(t1);
                    next_mask.ip_or(adj[b + 64]);
                    t1 &= ~(1ULL << b);
                }
                
                // Filter by position of next digit
                mask = next_mask & digit_pos[next_d];
                if (mask.empty()) {
                    possible = false;
                    break;
                }
            }
        }
        
        if (!possible) return val - 1;
        
        val++;
    }
}

int main() {
    // Seed random number generator
    rng.x += (uint32_t)time(NULL);

    init_adj();
    
    // Random initialization
    for (int i = 0; i < N; ++i) {
        grid_data[i] = rng.next_int(10);
        digit_pos[grid_data[i]].set(i);
        best_grid[i] = grid_data[i];
    }
    
    int best_score = calc_score(-1);
    
    // Run optimization for almost 60 seconds
    clock_t start_time = clock();
    double time_limit = 58.0; 
    long long iterations = 0;
    
    while (true) {
        // Check time every 256 iterations to avoid overhead
        if ((iterations & 255) == 0) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
        }
        iterations++;
        
        // Hill Climbing / Local Search Step
        // Mutate: Change one cell to a random digit
        int idx = rng.next_int(N);
        int old_val = grid_data[idx];
        int new_val = rng.next_int(10);
        
        if (old_val == new_val) continue;
        
        // Update state (grid and bitmasks)
        if (idx < 64) digit_pos[old_val].v0 &= ~(1ULL << idx);
        else digit_pos[old_val].v1 &= ~(1ULL << (idx - 64));
        
        if (idx < 64) digit_pos[new_val].v0 |= (1ULL << idx);
        else digit_pos[new_val].v1 |= (1ULL << (idx - 64));
        
        grid_data[idx] = new_val;
        
        // Evaluate
        int new_score = calc_score(best_score);
        
        // Accept if score improves or stays same (to traverse plateaus)
        if (new_score >= best_score) {
            if (new_score > best_score) {
                best_score = new_score;
                for(int i=0; i<N; ++i) best_grid[i] = grid_data[i];
            }
            // Keep change
        } else {
            // Reject change - Revert state
            grid_data[idx] = old_val;
            
            if (idx < 64) digit_pos[new_val].v0 &= ~(1ULL << idx);
            else digit_pos[new_val].v1 &= ~(1ULL << (idx - 64));
            
            if (idx < 64) digit_pos[old_val].v0 |= (1ULL << idx);
            else digit_pos[old_val].v1 |= (1ULL << (idx - 64));
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