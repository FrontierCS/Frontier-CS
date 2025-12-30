#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <iomanip>
#include <cstring>
#include <cmath>

using namespace std;

// Maximum number of 64-bit words for the bitset. 
// 20 words support up to 1280 patterns, which should be sufficient given the constraints 
// and the nature of the problem (typically either N or M is small).
#define MAX_WORDS 20

int N, M;
int words_needed;

struct Bitset {
    uint64_t words[MAX_WORDS];

    // Default constructor does NOT initialize to zero for performance reasons.
    // Use zero() to initialize.
    Bitset() {}

    void zero() {
        memset(words, 0, sizeof(words));
    }

    void set(int i) {
        if ((i >> 6) < MAX_WORDS) {
            words[i >> 6] |= (1ULL << (i & 63));
        }
    }

    bool any() const {
        for(int i = 0; i < words_needed; ++i) {
            if(words[i]) return true;
        }
        return false;
    }
    
    bool operator<(const Bitset& other) const {
        for(int i = 0; i < words_needed; ++i) {
            if(words[i] != other.words[i]) return words[i] < other.words[i];
        }
        return false;
    }
};

// Optimized bitwise AND that only processes needed words
Bitset bit_and(const Bitset& a, const Bitset& b) {
    Bitset res;
    for(int i = 0; i < words_needed; ++i) {
        res.words[i] = a.words[i] & b.words[i];
    }
    return res;
}

vector<vector<Bitset>> precomputed;
map<Bitset, double> memo[105];

// DFS for small N without memoization (faster per node)
long long count_valid(int idx, const Bitset& mask) {
    if (idx == N) return 1;

    long long total = 0;
    for (int c = 0; c < 4; ++c) {
        Bitset next_mask = bit_and(mask, precomputed[idx][c]);
        if (next_mask.any()) {
            total += count_valid(idx + 1, next_mask);
        }
    }
    return total;
}

// DFS with memoization for larger N
double solve_memo(int idx, const Bitset& mask) {
    if (idx == N) return 1.0;
    
    if (memo[idx].count(mask)) return memo[idx][mask];

    double prob = 0;
    for (int c = 0; c < 4; ++c) {
        Bitset next_mask = bit_and(mask, precomputed[idx][c]);
        if (next_mask.any()) {
            prob += 0.25 * solve_memo(idx + 1, next_mask);
        }
    }
    return memo[idx][mask] = prob;
}

// Check if set of strings matched by pattern i is a subset of pattern j
bool is_subset(int i, int j, const vector<string>& pats) {
    for (int k = 0; k < N; ++k) {
        // If pats[j][k] is '?', it matches anything, so pats[i][k] condition is always a subset (specific or ?)
        // If pats[j][k] is a character, pats[i][k] must be the same character to be a subset.
        if (pats[j][k] != '?') {
            if (pats[i][k] != pats[j][k]) return false;
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    vector<string> raw_patterns(M);
    for (int i = 0; i < M; ++i) cin >> raw_patterns[i];

    // Preprocessing: Remove redundant patterns
    // If pattern i is a subset of pattern j, then i is redundant for the union.
    vector<bool> keep(M, true);
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            // Check if i is subset of j
            if (is_subset(i, j, raw_patterns)) {
                // If they are identical, remove one (keep smaller index)
                if (raw_patterns[i] == raw_patterns[j]) {
                    if (i > j) keep[i] = false;
                } else {
                    // i is strict subset of j
                    keep[i] = false; 
                }
                if (!keep[i]) break;
            }
        }
    }

    vector<string> patterns;
    for (int i = 0; i < M; ++i) {
        if (keep[i]) patterns.push_back(raw_patterns[i]);
    }
    M = patterns.size();
    
    if (M == 0) {
        cout << fixed << setprecision(10) << 0.0 << endl;
        return 0;
    }

    words_needed = (M + 63) / 64;
    
    // Initialize precomputed masks
    precomputed.resize(N, vector<Bitset>(4));
    for(int j=0; j<N; ++j) 
        for(int k=0; k<4; ++k) 
            precomputed[j][k].zero();

    for (int idx = 0; idx < M; ++idx) {
        for (int j = 0; j < N; ++j) {
            char c = patterns[idx][j];
            if (c == '?') {
                for(int k=0; k<4; ++k) precomputed[j][k].set(idx);
            } else {
                int val = 0;
                if (c == 'A') val = 0;
                else if (c == 'C') val = 1;
                else if (c == 'G') val = 2;
                else if (c == 'T') val = 3;
                precomputed[j][val].set(idx);
            }
        }
    }

    Bitset initial_mask;
    initial_mask.zero();
    for(int i=0; i<M; ++i) initial_mask.set(i);

    cout << fixed << setprecision(10);

    // Heuristic: If N is small enough, brute force with pruning (raw DFS) is faster due to low overhead.
    // If N is larger, the number of branches explodes, so we need memoization.
    if (N <= 14) {
        long long valid_count = count_valid(0, initial_mask);
        double prob = (double)valid_count / pow(4.0, N);
        cout << prob << endl;
    } else {
        double prob = solve_memo(0, initial_mask);
        cout << prob << endl;
    }

    return 0;
}