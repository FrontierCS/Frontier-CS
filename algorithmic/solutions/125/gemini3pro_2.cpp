#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global tracker for the current response from the device
int current_r = 0;

// Wrapper for query to update current_r and return the difference
// diff = new_r - old_r
// +1: added a new mineral kind
// -1: removed a mineral kind that was unique
//  0: added a duplicate kind or removed one of a pair
int safe_query(int x) {
    cout << "? " << x << endl;
    int r;
    if (!(cin >> r)) exit(0);
    int diff = r - current_r;
    current_r = r;
    return diff;
}

void answer(int a, int b) {
    cout << "! " << a << " " << b << endl;
}

// S: elements in device (subset of Firsts)
// L: elements to match (subset of Seconds)
// s_in: boolean context, true if the current S subset is logically IN the device
// l_in: boolean state, true if the elements of L are currently IN the device
void recursive_solve(vector<int>& S, vector<int>& L, bool s_in, bool l_in) {
    if (L.empty()) {
        // If no elements to match, just maintain S consistency if needed.
        // Based on the flow, we don't need to explicitly act.
        return;
    }
    
    // Base case: S has 1 element. All y in L must match this single element.
    if (S.size() == 1) {
        for (int y : L) {
            answer(S[0], y);
        }
        return;
    }

    // Split S into Left and Right halves
    int mid = S.size() / 2;
    vector<int> S_L(S.begin(), S.begin() + mid);
    vector<int> S_R(S.begin() + mid, S.end());

    // Configure S state for partition: We need S_L IN and S_R OUT.
    if (s_in) { 
        // Current: S IN (S_L U S_R IN).
        // Action: Remove S_R.
        for (int x : S_R) safe_query(x);
    } else { 
        // Current: S OUT.
        // Action: Insert S_L.
        for (int x : S_L) safe_query(x);
    }

    vector<int> L_L, L_R;
    L_L.reserve(L.size());
    L_R.reserve(L.size());
    
    // Determine the state of L for the next recursion level to minimize queries.
    // We flip the state at each level.
    bool next_l_in = !l_in; 

    // Partition L based on matches with S_L (IN) or S_R (OUT)
    for (int y : L) {
        int diff = safe_query(y);
        
        if (l_in) { 
            // y was IN, now Removed.
            // If match was in S_L (IN): removal doesn't change unique count (pair broken but kind stays). diff == 0.
            // If match was in S_R (OUT): removal removes the only copy. diff == -1.
            if (diff == 0) L_L.push_back(y); // Matches S_L
            else L_R.push_back(y);           // Matches S_R
        } else { 
            // y was OUT, now Inserted.
            // If match in S_L (IN): insertion completes pair. diff == 0.
            // If match in S_R (OUT): insertion adds new kind. diff == +1.
            if (diff == 0) L_L.push_back(y); // Matches S_L
            else L_R.push_back(y);           // Matches S_R
        }
    }

    // Recurse for Left half
    // Context: S_L is currently IN. L_L is in state `next_l_in`.
    recursive_solve(S_L, L_L, true, next_l_in); 
    
    // Prepare for Right half
    // After Left return, S_L is IN (and matched L_L is effectively invisible).
    // We need to match L_R against S_R.
    // We insert S_R. S_L stays IN.
    // Effectively this sets the state for S_R to be IN.
    for (int x : S_R) safe_query(x); 
    
    // Recurse for Right half
    // Context: S_R is IN. L_R is in state `next_l_in`.
    recursive_solve(S_R, L_R, true, next_l_in); 
    
    // After Right return, S_R is IN. S_L is IN.
    // Thus S is IN, satisfying the contract if this function was called with s_in=true.
    // If called with s_in=false, the parent will handle S_L removal? 
    // Actually, based on the traversal:
    // If parent was Left: expect S_L IN. We return S IN. S_R is extra.
    // Parent "Insert S_R" logic handles the sibling.
    // The consistency is maintained by the alternating checks.
}

int main() {
    // Optimization for fast I/O
    std::ios_base::sync_with_stdio(false);
    
    int N;
    if (!(cin >> N)) return 0;
    
    vector<int> S, L;
    S.reserve(N);
    L.reserve(N);

    // Initial pass to separate Firsts (S) and Seconds (L)
    for (int i = 1; i <= 2 * N; ++i) {
        int diff = safe_query(i);
        if (diff == 1) {
            // First occurrence
            S.push_back(i);
        } else {
            // Second occurrence
            L.push_back(i);
            // Remove from device so L starts OUT
            safe_query(i); 
        }
    }
    
    // Start recursion
    // S is IN, L is OUT
    recursive_solve(S, L, true, false);
    
    return 0;
}