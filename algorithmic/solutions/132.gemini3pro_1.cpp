#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <bitset>

using namespace std;

// Number of positions
const int N = 1000;
// Number of robots/queries. M=26 allows for high score (R <= 30)
// and ensures low collision probability.
const int M = 26; 
const int MAX_SYNDROME = 1 << M;

// Global bitset to track used syndromes. 
// Size 2^26 bits = 64 Mbit = 8 MB. Fits easily in memory (512 MB limit).
std::bitset<MAX_SYNDROME> used_syndromes;

int codes[N + 1];

int main() {
    // Optimization for I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int R_in, H_in;
    if (!(cin >> R_in >> H_in)) return 0;

    // Use a fixed seed. The strategy relies on finding a valid code configuration.
    // M=26 provides a large enough space that a greedy random strategy works with high probability.
    mt19937 rng(5489u); 
    
    // Mask to keep only M bits
    int mask = (1 << M) - 1;

    // To verify uniqueness within a batch efficiently
    vector<int> batch;
    batch.reserve(N);

    for (int i = 1; i <= N; ++i) {
        bool success = false;
        int trials = 0;
        // Try to find a code for position i that doesn't conflict with any previous pairs
        // With M=26, the density of used syndromes is low (< 1%), so we expect to find one quickly.
        // We limit trials to avoid TLE, though average case is very small.
        while (trials < 2000) {
            trials++;
            int v = rng() & mask;
            
            // Collect all new syndromes that would be formed if we use v
            // These are {v} (representing pair {i,i}) and {v | codes[j]} for all j < i (pairs {i,j})
            batch.clear();
            
            // Check v itself
            if (used_syndromes[v]) {
                continue; 
            }
            batch.push_back(v);

            bool collision = false;
            for (int j = 1; j < i; ++j) {
                int s = v | codes[j];
                // Check against previously confirmed syndromes
                if (used_syndromes[s]) {
                    collision = true;
                    break;
                }
                batch.push_back(s);
            }
            if (collision) continue;

            // Check for collisions within the new batch itself
            sort(batch.begin(), batch.end());
            for (size_t k = 0; k < batch.size() - 1; ++k) {
                if (batch[k] == batch[k+1]) {
                    collision = true;
                    break;
                }
            }
            if (collision) continue;

            // If we reach here, v is valid
            success = true;
            codes[i] = v;
            // Mark new syndromes as used
            for (int s : batch) {
                used_syndromes[s] = 1;
            }
            break;
        }

        if (!success) {
            // Fallback in the unlikely event of failure: pick a random code.
            // This might cause ambiguity but we proceed to output a valid format.
            codes[i] = rng() & mask;
        }
    }

    // Output queries
    // We send M queries corresponding to the M bits.
    for (int b = 0; b < M; ++b) {
        vector<int> positions;
        for (int i = 1; i <= N; ++i) {
            if ((codes[i] >> b) & 1) {
                positions.push_back(i);
            }
        }
        cout << "? " << positions.size();
        for (int p : positions) {
            cout << " " << p;
        }
        cout << "\n";
    }
    // Signal end of queries to receive answers
    cout << "@" << endl;

    // Read response
    int L;
    cin >> L;
    int res_syndrome = 0;
    for (int i = 0; i < L; ++i) {
        int val;
        cin >> val;
        if (val) {
            res_syndrome |= (1 << i);
        }
    }

    // Decode: find the pair {i, j} such that codes[i] | codes[j] == res_syndrome
    for (int i = 1; i <= N; ++i) {
        // Pruning: The true positions must be a subset of the result syndrome
        if ((codes[i] & res_syndrome) != codes[i]) continue;

        for (int j = i; j <= N; ++j) {
            if ((codes[j] & res_syndrome) != codes[j]) continue;
            
            if ((codes[i] | codes[j]) == res_syndrome) {
                cout << "! " << i << " " << j << endl;
                return 0;
            }
        }
    }

    return 0;
}