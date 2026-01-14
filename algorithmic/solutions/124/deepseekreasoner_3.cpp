#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    vector<int> parity(n+1, 0); // parity[i] = answer of query (1,i) for i>=2
    vector<int> r(n+1, 0);      // r[i] = answer of all-but-i query
    
    // Step 1: get parity relations with index 1
    for (int i = 2; i <= n; ++i) {
        cout << "? 2 1 " << i << endl;
        cout.flush();
        int ans;
        cin >> ans;
        parity[i] = ans;
    }
    
    // Step 2: all-but-i queries
    for (int i = 1; i <= n; ++i) {
        cout << "? " << n-1;
        for (int j = 1; j <= n; ++j) {
            if (j != i) cout << " " << j;
        }
        cout << endl;
        cout.flush();
        cin >> r[i];
    }
    
    if (n == 2) {
        // Trivial case
        cout << "! 1 2" << endl;
        cout.flush();
        return 0;
    }
    
    // Find the two indices where r[i] == 1
    vector<int> S;
    for (int i = 1; i <= n; ++i) {
        if (r[i] == 1) S.push_back(i);
    }
    int a = S[0], b = S[1];
    
    int p1, idx1, idxn; // p1 = value at index 1, idx1 = index of value 1, idxn = index of value n
    int T = n * (n + 1) / 2;
    
    if (a == 1 || b == 1) {
        // Case 1: index 1 is among the special ones -> p1 = 1
        p1 = 1;
        if (a == 1) {
            idx1 = a;
            idxn = b;
        } else {
            idx1 = b;
            idxn = a;
        }
    } else {
        // Case 2: index 1 is not special, need to determine p1 and assignment
        int ansA, ansB;
        // Query A: all indices except {1, a}
        cout << "? " << n-2;
        for (int j = 1; j <= n; ++j) {
            if (j != 1 && j != a) cout << " " << j;
        }
        cout << endl;
        cout.flush();
        cin >> ansA;
        
        // Query B: all indices except {1, b}
        cout << "? " << n-2;
        for (int j = 1; j <= n; ++j) {
            if (j != 1 && j != b) cout << " " << j;
        }
        cout << endl;
        cout.flush();
        cin >> ansB;
        
        int mod = n - 2;
        bool found = false;
        for (int cand = 2; cand <= n/2; ++cand) {
            // Try assignment (a=1, b=n)
            bool pa_ok1 = (parity[a] == ((cand % 2 == 1) ? 1 : 0));
            bool pb_ok1 = (parity[b] == ((cand % 2 == 0) ? 1 : 0));
            if (pa_ok1 && pb_ok1) {
                bool condA = ((T - cand - 1) % mod == 0);
                bool condB = ((T - cand - n) % mod == 0);
                if (condA == (ansA == 1) && condB == (ansB == 1)) {
                    p1 = cand;
                    idx1 = a;
                    idxn = b;
                    found = true;
                    break;
                }
            }
            // Try assignment (a=n, b=1)
            bool pa_ok2 = (parity[a] == ((cand % 2 == 0) ? 1 : 0));
            bool pb_ok2 = (parity[b] == ((cand % 2 == 1) ? 1 : 0));
            if (pa_ok2 && pb_ok2) {
                bool condA = ((T - cand - n) % mod == 0);
                bool condB = ((T - cand - 1) % mod == 0);
                if (condA == (ansA == 1) && condB == (ansB == 1)) {
                    p1 = cand;
                    idx1 = b;
                    idxn = a;
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            // Should not happen with a valid interactor
            return 1;
        }
    }
    
    // We now know p1, idx1 (position of 1), idxn (position of n)
    vector<int> perm(n+1, 0);
    vector<bool> determined(n+1, false);
    perm[1] = p1;
    perm[idx1] = 1;
    perm[idxn] = n;
    determined[1] = determined[idx1] = determined[idxn] = true;
    
    // Compute absolute parity for each index
    vector<int> abs_parity(n+1);
    abs_parity[1] = p1 % 2;
    for (int i = 2; i <= n; ++i) {
        if (parity[i] == 1) {
            abs_parity[i] = p1 % 2;
        } else {
            abs_parity[i] = 1 - (p1 % 2);
        }
    }
    
    // Step 5: determine the remaining values
    int mod = n - 2;
    for (int i = 1; i <= n; ++i) {
        if (determined[i]) continue;
        
        int r1, r2, r3;
        // Query1: exclude i and idx1
        cout << "? " << n-2;
        for (int j = 1; j <= n; ++j) {
            if (j != i && j != idx1) cout << " " << j;
        }
        cout << endl;
        cout.flush();
        cin >> r1;
        
        // Query2: exclude i and idxn
        cout << "? " << n-2;
        for (int j = 1; j <= n; ++j) {
            if (j != i && j != idxn) cout << " " << j;
        }
        cout << endl;
        cout.flush();
        cin >> r2;
        
        // Query3: triple {i, idx1, idxn}
        cout << "? 3 " << i << " " << idx1 << " " << idxn << endl;
        cout.flush();
        cin >> r3;
        
        // Try all possible values v
        vector<bool> used(n+1, false);
        used[perm[1]] = used[1] = used[n] = true;
        int found_val = -1;
        for (int v = 1; v <= n; ++v) {
            if (used[v]) continue;
            if ((v % 2) != abs_parity[i]) continue;
            
            bool cond1 = ((T - v - 1) % mod == 0);
            if ((cond1 && r1 != 1) || (!cond1 && r1 != 0)) continue;
            
            bool cond2 = ((T - v - n) % mod == 0);
            if ((cond2 && r2 != 1) || (!cond2 && r2 != 0)) continue;
            
            bool cond3 = ((v + 1 + n) % 3 == 0);
            if ((cond3 && r3 != 1) || (!cond3 && r3 != 0)) continue;
            
            found_val = v;
            break;
        }
        if (found_val == -1) {
            // Should not happen
            return 1;
        }
        perm[i] = found_val;
        determined[i] = true;
    }
    
    // Output the answer
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << perm[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}