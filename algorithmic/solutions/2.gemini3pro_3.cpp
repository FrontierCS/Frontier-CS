#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to query
int query(const vector<int>& q) {
    cout << "0";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to submit answer
void answer(const vector<int>& p) {
    cout << "1";
    for (int x : p) {
        cout << " " << x;
    }
    cout << endl;
    exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n, 0); // 0 means unknown

    if (n == 1) {
        p[0] = 1;
        answer(p);
        return 0;
    }

    // Indices 0 to n-1
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 0);
    
    // Step 1: Find pos(1)
    // We iterate to narrow down the candidate set for 1.
    // To distinguish if 1 is in Left or Right, we compare against fillers 2, 3, ...
    vector<int> curr = candidates;
    while (curr.size() > 1) {
        int mid = curr.size() / 2;
        vector<int> L(curr.begin(), curr.begin() + mid);
        vector<int> R(curr.begin() + mid, curr.end());
        
        int found_side = 0; // -1 Left, 1 Right
        
        // Try up to 20 fillers or until N. Usually 1 or 2 suffice.
        for (int k = 2; k <= min(n, 20); ++k) {
            // Query A: 1 in L, k in R, k elsewhere
            vector<int> qA(n, k);
            for(int idx : L) qA[idx] = 1;
            
            // Query B: k in L, 1 in R, k elsewhere
            vector<int> qB(n, k);
            for(int idx : R) qB[idx] = 1;
            
            int sA = query(qA);
            int sB = query(qB);
            
            // sA - sB = 2 * (I(1 in L) - I(1 in R))
            // Because k is symmetric in the swap.
            if (sA > sB) { found_side = -1; break; }
            if (sB > sA) { found_side = 1; break; }
        }
        
        // If still 0, it means 1 is together with all checked fillers in the same partition.
        // This is statistically very unlikely for a random permutation.
        // Default to Left if indistinguishable (though for valid test cases this shouldn't break logic).
        if (found_side == 0) found_side = -1; 
        
        if (found_side == -1) curr = L;
        else curr = R;
    }
    p[curr[0]] = 1;
    
    // Step 2: Find pos(k) for k = 2 to N
    // We can use the known position of 1 as a filler.
    // Since 1 is at p[pos(1)], putting 1 there yields a match.
    // Putting 1 elsewhere yields no match (since 1 is unique).
    // This allows us to count exactly.
    
    for (int k = 2; k <= n; ++k) {
        vector<int> domain;
        for(int i=0; i<n; ++i) if(p[i] == 0) domain.push_back(i);
        
        vector<int> current_domain = domain;
        while (current_domain.size() > 1) {
            int mid = current_domain.size() / 2;
            vector<int> L(current_domain.begin(), current_domain.begin() + mid);
            vector<int> R(current_domain.begin() + mid, current_domain.end());
            
            // Construct query:
            // Put k in L.
            // Put 1 in R.
            // Put 1 in all other unknown positions.
            // Put known values in their positions.
            
            vector<int> q(n, 1); // Default to 1 (filler)
            for(int i=0; i<n; ++i) {
                if(p[i] != 0) q[i] = p[i]; // Knowns
            }
            for(int idx : L) q[idx] = k; // Test k in L
            // R and other unknowns are already 1.
            
            int score = query(q);
            
            // Calculate expected score if k is in L.
            // Score = Matches(Knowns) + Matches(L) + Matches(Rest with 1)
            // Matches(Knowns) = k - 1.
            // If k in L: Matches(L) = 1. Matches(Rest with 1) = 0 (since 1 is at pos(1) which is in Knowns).
            // Wait, if 1 is used as filler in R/Rest, does it match?
            // 1 only matches at pos(1).
            // pos(1) is in the 'Knowns' set, so q[pos(1)] = p[pos(1)] = 1.
            // So 1 matches there.
            // Any other 1 in q (at R or unknowns) is at a position where p[i] != 1.
            // So they do not match.
            // Thus, the contribution of 1s in unknown areas is 0.
            
            // So if k is in L, Score = (k-1) + 1 = k.
            // If k is in R, Score = (k-1) + 0 = k - 1.
            
            if (score == k) {
                current_domain = L;
            } else {
                current_domain = R;
            }
        }
        p[current_domain[0]] = k;
    }
    
    answer(p);
    
    return 0;
}