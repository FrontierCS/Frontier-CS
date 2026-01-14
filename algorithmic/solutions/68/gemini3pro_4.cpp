#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to query a pen
// Returns 1 if ink was consumed (pen had ink), 0 if empty
int query(int pen) {
    cout << "0 " << pen << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Should not happen based on problem statement
    return res;
}

void solve() {
    int n;
    cin >> n;
    
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 0);
    
    // We use a "King of the Hill" / Tournament strategy.
    // We maintain a list of candidate pens.
    // We iteratively pick two pens and pit them against each other.
    // If a pen runs out of ink (returns 0), it is discarded.
    // If it has ink, it survives but loses 1 unit.
    // By putting survivors back into the pool (at the beginning),
    // we allow strong pens (high ink) to eliminate multiple weak pens.
    // The total ink in the top pens is sufficient to "pay" for the elimination
    // of the bottom pens while maintaining enough remaining ink to satisfy the condition.
    
    while (candidates.size() > 2) {
        // Pick two candidates from the back
        int u = candidates.back(); candidates.pop_back();
        int v = candidates.back(); candidates.pop_back();
        
        // Query u
        int res_u = query(u);
        if (res_u == 0) {
            // u is empty, remove it. v goes back to the pool to fight someone else.
            candidates.push_back(v);
            continue;
        }
        
        // u is not empty (decremented). Query v.
        int res_v = query(v);
        if (res_v == 0) {
            // v is empty, remove it. u goes back to the pool.
            candidates.push_back(u);
            continue;
        }
        
        // Both u and v had ink and were decremented.
        // We put them back at the *beginning* of the list.
        // This ensures they will fight different opponents next, distributing the "damage".
        // If we put them at the end, they would just fight each other until one dies, which is inefficient.
        candidates.insert(candidates.begin(), u);
        candidates.insert(candidates.begin(), v);
    }
    
    // Output the final two pens
    cout << "1 " << candidates[0] << " " << candidates[1] << endl;
}

int main() {
    // Optimize I/O operations
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