#include <iostream>
#include <vector>
#include <random>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int R_in, H_in;
    if (!(cin >> R_in >> H_in)) return 0;

    // We target using 26 robots. According to the grading formula:
    // rmax <= 30 => score = -20/3 * rmax + 820/3
    // For rmax = 26, score = -520/3 + 820/3 = 300/3 = 100.
    // 2^26 is approx 67 million, which fits in memory (67MB for vector<uint8_t>).
    // This size also ensures a very low collision probability for picking signatures.
    int num_robots = 26;
    if (R_in < num_robots) num_robots = R_in;

    int N = 1000;
    vector<int> masks;
    masks.reserve(N);

    // Direct addressing array to mark used signatures (pair unions)
    // used[mask] = 1 if 'mask' is the bitwise OR of some pair of generated signatures
    int max_val = 1 << num_robots;
    vector<uint8_t> used(max_val, 0);

    // Fixed seed for determinism
    mt19937 rng(5489u); 
    uniform_int_distribution<int> dist(1, max_val - 1);

    // Greedily generate masks for each position
    for (int i = 0; i < N; ++i) {
        while (true) {
            int cand = dist(rng);
            bool ok = true;
            
            // We require that for the new candidate 'cand', for all existing masks 'm',
            // the union (cand | m) has not been seen before.
            // Also (cand | cand) i.e. cand itself must not be seen.
            // This ensures that every pair of positions has a unique OR signature.
            
            if (used[cand]) {
                ok = false;
            } else {
                for (int m : masks) {
                    if (used[cand | m]) {
                        ok = false;
                        break;
                    }
                }
            }

            if (ok) {
                masks.push_back(cand);
                // Mark signatures formed by this new mask combined with all previous ones (and itself)
                used[cand] = 1; 
                for (size_t j = 0; j < masks.size() - 1; ++j) {
                    used[cand | masks[j]] = 1;
                }
                break;
            }
            // If not ok, try another random candidate.
            // With 2^26 space and ~500,000 used entries, collision rate is low, so this terminates quickly.
        }
    }

    // Send queries
    // Query j sends a robot to all positions i where the j-th bit of mask[i] is set.
    for (int r = 0; r < num_robots; ++r) {
        vector<int> p;
        for (int i = 0; i < N; ++i) {
            if ((masks[i] >> r) & 1) {
                p.push_back(i + 1);
            }
        }
        cout << "? " << p.size();
        for (int x : p) cout << " " << x;
        cout << endl;
    }
    
    // Signal end of sending
    cout << "@" << endl;

    // Read result
    int L;
    cin >> L;
    vector<int> response(L);
    int res_mask = 0;
    for (int i = 0; i < L; ++i) {
        cin >> response[i];
        if (response[i]) {
            res_mask |= (1 << i);
        }
    }

    // Decode the result
    // Iterate over all pairs of positions. The correct pair {u, v} will satisfy mask[u] | mask[v] == res_mask.
    // Due to our construction, this signature is unique.
    for (int i = 0; i < N; ++i) {
        // Optimization: The correct mask must be a submask of the result
        if ((masks[i] | res_mask) != res_mask) continue;
        
        for (int j = i; j < N; ++j) {
            if ((masks[i] | masks[j]) == res_mask) {
                cout << "! " << i + 1 << " " << j + 1 << endl;
                return 0;
            }
        }
    }

    return 0;
}