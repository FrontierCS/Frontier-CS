#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

// Helper to flush output
void query_out(const string& s) {
    cout << "? " << s << endl;
}

int read_int() {
    int x;
    cin >> x;
    return x;
}

int n;

// Function to perform query
// S is a boolean vector where S[i] is true if vertex i+1 is in the subset
int ask(const vector<bool>& S) {
    string s = "";
    for (int i = 0; i < n; ++i) {
        s += (S[i] ? '1' : '0');
    }
    query_out(s);
    return read_int();
}

void solve() {
    cin >> n;
    
    vector<int> K;
    K.push_back(0); // Start with vertex 1 (0-indexed)
    
    vector<int> U;
    for (int i = 1; i < n; ++i) U.push_back(i);
    
    // K is the set of vertices currently in our component
    // U is the set of unknown vertices
    
    while (!U.empty()) {
        // Construct query for K
        vector<bool> S_vec(n, false);
        for (int x : K) S_vec[x] = true;
        
        int q = ask(S_vec);
        if (q == 0) {
            // Disconnected
            cout << "! 0" << endl;
            return;
        }
        
        // Binary search to find a vertex in U to add to K
        // We look for the largest index `idx` in U such that query(K U {U[idx]...U[end]}) == 0
        // The vertex U[idx] is the one to add.
        
        // Range of indices in U: [0, m] where m = U.size()
        // idx = m corresponds to empty suffix (just K) which has query > 0 (checked above)
        // idx = 0 corresponds to full U union K which is V, query = 0
        
        int low = 0, high = U.size(); 
        int best_idx = 0;
        
        // We know for idx=0, query is 0.
        // We know for idx=U.size(), query is > 0.
        // We want largest idx such that query is 0.
        
        // Binary search:
        // Invariant: query(low) == 0
        // We try to push low higher.
        
        high = U.size() - 1; // max possible index for a vertex
        int ans = 0; // Default to 0
        
        int L = 1, R = U.size(); // Range for the split point
        // We want to find boundary between 0 and >0
        // Check mid.
        // Suffix starts at mid.
        
        // Actually simpler:
        // We want largest k such that query(K U {u_k ... }) == 0.
        // We know k=0 works (query(V)=0).
        // We check k using BS.
        
        int l = 0, r = U.size();
        while (l < r) {
            int mid = (l + r + 1) / 2;
            if (mid == U.size()) {
                // Suffix is empty. query(K). We know it is > 0.
                // So mid cannot be the answer for "== 0".
                r = mid - 1;
                continue;
            }
            
            // Construct set
            vector<bool> tempS = S_vec;
            for (int i = mid; i < U.size(); ++i) {
                tempS[U[i]] = true;
            }
            
            if (ask(tempS) == 0) {
                l = mid;
            } else {
                r = mid - 1;
            }
        }
        
        // l is the index of the vertex to add
        int v = U[l];
        K.push_back(v);
        U.erase(U.begin() + l);
    }
    
    cout << "! 1" << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}