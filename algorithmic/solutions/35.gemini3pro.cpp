#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform a query
// Returns 1 if x is in S, 0 otherwise
int query(int x, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << x << " " << S.size();
    for (int i : S) {
        cout << " " << i;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Global random engine
mt19937 rng(1337);

// DFS to find the unique element
// candidates: list of possible numbers
// indices: list of positions where these candidates might be located
int dfs(vector<int> candidates, vector<int> indices) {
    // Base cases
    if (candidates.empty()) return -1;
    if (candidates.size() == 1) return candidates[0];
    if (indices.empty()) return candidates[0]; // Should not happen ideally

    int m = indices.size();
    
    // Split indices into two roughly equal sets
    shuffle(indices.begin(), indices.end(), rng);
    int split_size = m / 2;
    if (split_size == 0) split_size = 1;

    vector<int> S;
    S.reserve(split_size);
    for(int i=0; i<split_size; ++i) S.push_back(indices[i]);

    vector<int> S_complement;
    S_complement.reserve(m - split_size);
    for(int i=split_size; i<m; ++i) S_complement.push_back(indices[i]);

    vector<int> C0, C1;
    C0.reserve(candidates.size());
    C1.reserve(candidates.size());

    // Query all current candidates against set S
    for (int x : candidates) {
        int res = query(x, S);
        if (res == 0) {
            // x is not in S, so it must be in S_complement (fully)
            C0.push_back(x);
        } else {
            // x is in S (partially or fully)
            C1.push_back(x);
        }
    }

    // Heuristic: Candidates in C0 are "cleaner" because doubles in C0 
    // must have both copies in S_complement (prob 0.25), 
    // whereas single in C0 is prob 0.5. 
    // So C0 is enriched with the target. Search C0 first.
    
    int res = dfs(C0, S_complement);
    if (res != -1) return res;

    // If not found in C0, search in C1.
    // For x in C1, we only care about their occurrence in S.
    return dfs(C1, S);
}

void solve() {
    int n;
    if (!(cin >> n)) exit(0);
    if (n == -1) exit(0);

    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);
    
    vector<int> indices(2 * n - 1);
    iota(indices.begin(), indices.end(), 1);

    int ans = dfs(candidates, indices);
    
    // If search fails (should not happen with correct logic), guess
    if (ans == -1) ans = 1; 
    
    cout << "! " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}