#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

// Helper to interact with the judge
int query(int n, const vector<int>& subset) {
    string s(n, '0');
    for (int x : subset) {
        if (x >= 1 && x <= n) {
            s[x - 1] = '1';
        }
    }
    cout << "? " << s << endl;
    int ans;
    cin >> ans;
    return ans;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // Corner case N=1 is implicitly connected
    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    // Initial components: each vertex is a component
    vector<vector<int>> comps(n + 1);
    for (int i = 1; i <= n; ++i) {
        comps[i].push_back(i);
    }

    // active_comps stores the IDs of current components (initially 1..N)
    vector<int> active_comps(n);
    iota(active_comps.begin(), active_comps.end(), 1);

    // Cache f(C) values for active components
    vector<int> f_vals(n + 1);
    for (int i = 1; i <= n; ++i) {
        f_vals[i] = query(n, comps[i]);
    }

    while (active_comps.size() > 1) {
        int u_id = active_comps[0];
        
        // If the component has no outgoing edges to ANY node outside,
        // and it's not the whole graph, then disconnected.
        if (f_vals[u_id] == 0) {
            cout << "! 0" << endl;
            return;
        }

        // We try to find another component v_id connected to u_id or part of a path from u_id.
        // We search among other active components: active_comps[1 ... size-1].
        int L = 1;
        int R = active_comps.size() - 1;
        
        // Binary search like strategy to pinpoint a component with 'activity'
        while (L < R) {
            int mid = L + (R - L) / 2;
            
            // We split the candidate range into Left [L, mid] and Right [mid+1, R].
            // We check if the Right group has any edges to V \ Right Group.
            // This query effectively checks if the Right group is isolated from the rest.
            
            string s(n, '1'); // Start with all included (representing V)
            
            for (int k = mid + 1; k <= R; ++k) {
                int c_id = active_comps[k];
                for (int node : comps[c_id]) {
                    s[node - 1] = '0'; // Exclude nodes in Right Group
                }
            }
            
            cout << "? " << s << endl;
            int res;
            cin >> res;
            
            if (res > 0) {
                // Right group has connection to outside (which includes u_id).
                // We follow the activity towards Right.
                L = mid + 1;
            } else {
                // Right group is isolated from the rest of V.
                // Since u_id is in the rest, u_id cannot connect to Right Group.
                // The neighbor of u_id (if any in this range) must be in Left Group.
                R = mid;
            }
        }
        
        int v_loc = L;
        int v_id = active_comps[v_loc];

        // Try to merge u_id and v_id
        vector<int> combined = comps[u_id];
        combined.insert(combined.end(), comps[v_id].begin(), comps[v_id].end());
        
        int f_combined = query(n, combined);
        
        // Calculate number of edges between component u and component v
        // Formula derived from Inclusion-Exclusion on neighbor sets:
        // 2 * edges(u, v) = f(u) + f(v) - f(u U v)
        int edges = (f_vals[u_id] + f_vals[v_id] - f_combined) / 2;
        
        if (edges > 0) {
            // Successful merge
            comps[u_id] = combined;
            f_vals[u_id] = f_combined;
            
            // Remove v_id from active_comps
            active_comps.erase(active_comps.begin() + v_loc);
            // u_id is kept at front
        } else {
            // Failed to merge u and v directly.
            // This implies v_id was 'active' because it connects to something else in the graph,
            // but not necessarily u_id.
            // Strategy: Move u to back, move v to front.
            // This effectively traverses the path of connections.
            
            active_comps.erase(active_comps.begin()); // remove u
            
            // v was at v_loc, indices shifted left by 1
            int new_v_loc = v_loc - 1;
            
            active_comps.erase(active_comps.begin() + new_v_loc); // remove v
            
            active_comps.insert(active_comps.begin(), v_id); // v to front
            active_comps.push_back(u_id); // u to back
        }
    }
    
    cout << "! 1" << endl;
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