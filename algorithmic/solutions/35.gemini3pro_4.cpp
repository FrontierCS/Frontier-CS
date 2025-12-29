#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to query the interactor
int query(int x, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << x << " " << S.size();
    for (int idx : S) {
        cout << " " << idx;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    int n;
    cin >> n;
    
    // Candidates initially 1 to n
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);
    
    // Total positions 1 to 2n-1
    int m = 2 * n - 1;
    vector<int> all_indices(m);
    iota(all_indices.begin(), all_indices.end(), 1);
    
    mt19937 rng(1337);
    
    while (candidates.size() > 1) {
        // Create a random mask S
        vector<int> indices = all_indices;
        shuffle(indices.begin(), indices.end(), rng);
        
        // Take first half as S
        int k = indices.size() / 2;
        vector<int> S(indices.begin(), indices.begin() + k);
        vector<int> S_complement(indices.begin() + k, indices.end());
        
        // Sort for cleaner output (optional but good for debugging)
        // sort(S.begin(), S.end());
        // sort(S_complement.begin(), S_complement.end());
        
        vector<int> C0; // Answer 0 on S
        vector<int> C1; // Answer 1 on S
        
        for (int x : candidates) {
            int res = query(x, S);
            if (res == 0) {
                C0.push_back(x);
            } else {
                C1.push_back(x);
            }
        }
        
        // For those in C1, check if they are also in S_complement
        // If yes -> Split -> Discard
        // If no -> Pure in S -> Keep
        
        vector<int> C1_pure;
        for (int x : C1) {
            // Optimization: if C1 is small, maybe we can stop earlier? 
            // But we need to eliminate splits.
            int res = query(x, S_complement);
            if (res == 0) {
                C1_pure.push_back(x);
            }
            // else: res == 1 implies split, so discard
        }
        
        // New candidates are C0 (Pure in S_complement) and C1_pure (Pure in S)
        candidates = C0;
        candidates.insert(candidates.end(), C1_pure.begin(), C1_pure.end());
    }
    
    cout << "! " << candidates[0] << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}