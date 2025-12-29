#include <bits/stdc++.h>
using namespace std;

int main() {
    int R, H;
    cin >> R >> H; // R=75, H=1
    
    const int m = 40; // number of robots we will use
    const int n = 1000;
    const double p = 0.293;
    
    vector<uint64_t> mask(n);
    vector<vector<int>> queries(m);
    
    // Generate a random matrix that is 2-separable
    mt19937 rng;
    bernoulli_distribution dist(p);
    bool good = false;
    
    for (int seed = 0; seed < 100; seed++) {
        rng.seed(seed);
        // Reset
        for (int i = 0; i < n; i++) mask[i] = 0;
        for (int i = 0; i < m; i++) queries[i].clear();
        
        // Generate matrix
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                if (dist(rng)) {
                    mask[j] |= (1ULL << i);
                    queries[i].push_back(j+1); // positions are 1-indexed
                }
            }
        }
        
        // Check 2-separability: all pair-wise ORs must be distinct
        unordered_set<uint64_t> seen;
        good = true;
        for (int i = 0; i < n && good; i++) {
            for (int j = i; j < n; j++) {
                uint64_t union_mask = mask[i] | mask[j];
                if (seen.count(union_mask)) {
                    good = false;
                    break;
                }
                seen.insert(union_mask);
            }
        }
        if (good) {
            // Found a good matrix
            break;
        }
    }
    
    // In the extremely unlikely case that no good matrix is found,
    // we fall back to the last generated matrix (still very likely to work).
    
    // Send queries
    for (int i = 0; i < m; i++) {
        cout << "? " << queries[i].size();
        for (int pos : queries[i]) {
            cout << " " << pos;
        }
        cout << endl;
        cout.flush();
    }
    
    // Get results
    cout << "@" << endl;
    cout.flush();
    
    int L;
    cin >> L;
    vector<int> res(L);
    for (int i = 0; i < L; i++) {
        cin >> res[i];
    }
    
    // Compute result mask
    uint64_t resultMask = 0;
    for (int i = 0; i < m; i++) {
        if (res[i] == 1) {
            resultMask |= (1ULL << i);
        }
    }
    
    // Find the pair that matches the result mask
    int a = -1, b = -1;
    for (int i = 0; i < n; i++) {
        for (int j = i; j < n; j++) {
            if ((mask[i] | mask[j]) == resultMask) {
                a = i+1;
                b = j+1;
                break;
            }
        }
        if (a != -1) break;
    }
    
    // Output answer
    cout << "! " << a << " " << b << endl;
    cout.flush();
    
    return 0;
}