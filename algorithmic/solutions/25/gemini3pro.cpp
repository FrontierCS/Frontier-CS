#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Function to perform a query
// Returns the number of vertices in V \ s that are connected to at least one vertex in s
int query(int n, const vector<int>& s) {
    if (s.empty()) return 0; 
    string q(n, '0');
    for (int x : s) {
        q[x - 1] = '1';
    }
    cout << "? " << q << endl;
    int ans;
    cin >> ans;
    return ans;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // A single vertex graph is connected
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    // Initially each vertex is a separate component
    vector<vector<int>> comps;
    comps.reserve(n);
    for (int i = 1; i <= n; ++i) {
        comps.push_back({i});
    }

    // We proceed by merging components. 
    // In each step, we take one component and find another component it "interacts" with.
    // Interaction means either a direct edge or a common neighbor.
    while (comps.size() > 1) {
        // Take the last component as the current one to grow
        vector<int> current = comps.back();
        comps.pop_back();

        int f_current = query(n, current);
        
        // If the current component has no neighbors outside, the graph is disconnected
        if (f_current == 0) {
            cout << "! 0" << endl;
            return;
        }

        // We use binary search on the remaining components to find one to merge with.
        // We look for a subset of components L such that 'current' interacts with L.
        int low = 0, high = comps.size() - 1;
        int target_idx = -1;

        while (low < high) {
            int mid = low + (high - low) / 2;
            
            // Construct set L from comps[low...mid]
            vector<int> L_set;
            for (int i = low; i <= mid; ++i) {
                L_set.insert(L_set.end(), comps[i].begin(), comps[i].end());
            }

            int f_L = query(n, L_set);
            
            // Construct Union = current U L_set
            vector<int> Union_set = current;
            Union_set.insert(Union_set.end(), L_set.begin(), L_set.end());
            
            int f_Union = query(n, Union_set);

            // Calculate interaction value based on inclusion-exclusion principle logic
            // f(A) + f(B) - f(A U B) = 2 * |Edges(A, B)| + |CommonNeighborsOutside(A U B)|
            // If val > 0, then A (current) and B (L_set) belong to the same connected component
            int val = f_current + f_L - f_Union;

            if (val > 0) {
                // Connection is in the left half
                high = mid;
            } else {
                // Connection must be in the right half
                low = mid + 1;
            }
        }
        target_idx = low;

        // Merge 'current' into 'comps[target_idx]'
        vector<int>& target = comps[target_idx];
        target.insert(target.end(), current.begin(), current.end());
    }

    // If we successfully merged all vertices into one component
    cout << "! 1" << endl;
}

int main() {
    // Optimization for faster I/O
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