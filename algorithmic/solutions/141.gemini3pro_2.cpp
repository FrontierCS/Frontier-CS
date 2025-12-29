#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    int d = n;
    vector<bool> is_dup(n + 1, false);
    int ops = 0;
    const int MAX_OPS = 100000;

    // Initial Reset
    cout << "R" << endl;
    ops += n; 

    // We keep track of which offset distances (difference between indices)
    // are covered by our query sequences.
    // With a memory of size k, a sequence of queries q_1, q_2, ... 
    // checks q_t against q_{t-1}, ..., q_{t-k}.
    // If the sequence has a constant stride S (i.e., q_i, q_i+S, q_i+2S...),
    // then q_t is compared against indices at distances S, 2S, ..., k*S in the original array.
    vector<bool> offset_covered(n, false);
    
    // Determine the list of strides to use.
    // We want to cover all offsets from 1 to n-1.
    // We iterate 1 to n-1, if an offset is not covered, we add it as a stride
    // and mark all multiples up to k*stride as covered.
    vector<int> strides;
    for (int s = 1; s < n; ++s) {
        if (!offset_covered[s]) {
            strides.push_back(s);
            // Mark covered offsets for this stride
            for (int j = 1; j <= k; ++j) {
                long long cov = (long long)s * j;
                if (cov < n) offset_covered[cov] = true;
                else break;
            }
        }
    }
    
    // Execute queries for each selected stride
    for (int s : strides) {
        if (ops >= MAX_OPS) break;

        // For a stride s, we form chains to cover all elements 1..n
        // We use a visited array to handle cycles/chains correctly.
        vector<bool> visited(n + 1, false);
        
        // Since n is a power of 2, if s is odd, one chain covers everything (permutation).
        // If s is even, we have gcd(s, n) chains.
        // We simply iterate start nodes.
        for (int start = 1; start <= n; ++start) {
            if (visited[start]) continue;
            if (ops >= MAX_OPS) break;

            // Traverse the chain starting at 'start' with stride 's'
            // We construct the sequence of indices first
            // Note: Generating the full sequence and then querying.
            // The memory is continuous across chains (we don't reset), 
            // which adds random useful comparisons but doesn't hurt.
            
            // To ensure we visit valid indices in range [1, n].
            // The simple logic "curr += s" works if we treat indices linearly.
            // But we must cover all pairs.
            // The logic "stride s covers offset s" implies linear distance.
            // So we simply iterate linearly: start, start+s, start+2s...
            
            long long curr = start;
            while (curr <= n) {
                // If we are close to limit, stop
                if (ops >= MAX_OPS) break;
                
                // We query every element in the chain to maintain the memory window context
                // even if we visited it in a previous stride pass.
                // However, the `visited` array here is for the CURRENT stride pass loops
                // to avoid starting a new chain on an element already processed in THIS pass.
                // Re-querying elements across different stride passes is necessary 
                // to check against new partners.
                
                // Perform query
                cout << "? " << curr << endl;
                ops++;
                
                char ans;
                cin >> ans;
                if (ans == 'Y') {
                    if (!is_dup[curr]) {
                        is_dup[curr] = true;
                        d--;
                    }
                }
                
                // Mark as visited for this stride pass
                visited[curr] = true;
                
                curr += s;
            }
        }
    }

    cout << "! " << d << endl;
    return 0;
}