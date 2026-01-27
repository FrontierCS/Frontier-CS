#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <cstdlib>

using namespace std;

// Function to perform a query
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int main() {
    // Fast I/O is not strictly necessary for interactive problems but good practice
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Create a list of indices 1 to n
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Shuffle indices to avoid worst-case scenarios and allow probabilistic assumptions
    random_device rd;
    mt19937 g(rd());
    shuffle(p.begin(), p.end(), g);

    // 'best' is our current candidate for the index holding value 0
    int best = p[0];
    int confidence = 0;
    
    // Stores the values (p[best] | p[i]) for the current 'best'
    // If 'best' is actually 0, this stores p[i].
    vector<int> known_values(n + 1, -1);

    for (int i = 1; i < n; ++i) {
        int curr = p[i];
        
        // Query best | curr. 
        // If best is 0, this gives us the value of curr immediately.
        int val_bc = query(best, curr);
        
        // Strategy:
        // If best == 0, then (best | curr) == curr.
        // Also (best | curr) should be a submask of (curr | w) for ANY w.
        // If (best | curr) is NOT a submask of (curr | w), then best CANNOT be 0 
        // (assuming curr | w is a random value).
        // Actually, if best=0, the condition always holds.
        // If condition fails, best is not 0.
        
        // We build confidence. If confidence is high, we skip verification to save queries.
        if (confidence < 12) {
            // Check 1: Pick a random witness w
            int w = -1;
            while (true) {
                w = p[g() % n];
                if (w != best && w != curr) break;
            }
            int val_cw = query(curr, w);
            
            // Check if (best | curr) is a subset of (curr | w)
            if ((val_bc & val_cw) != val_bc) {
                // Verification failed -> best is not 0.
                // Switch candidate to curr.
                best = curr;
                confidence = 0;
                // Previous values were relative to old best, discard them
                fill(known_values.begin(), known_values.end(), -1);
                continue; 
            }
            
            // Check 2: Pick another random witness w2 (if enough elements)
            // This reduces the probability of a false positive (where best != 0 but check passed)
            if (n >= 4) {
                int w2 = -1;
                while (true) {
                    w2 = p[g() % n];
                    if (w2 != best && w2 != curr && w2 != w) break;
                }
                int val_cw2 = query(curr, w2);
                
                if ((val_bc & val_cw2) != val_bc) {
                    best = curr;
                    confidence = 0;
                    fill(known_values.begin(), known_values.end(), -1);
                    continue;
                }
            }
            
            // If passed checks, we increase confidence in 'best'
            confidence++;
            known_values[curr] = val_bc;
        } else {
            // High confidence that 'best' is 0.
            // Skip expensive checks. We assume val_bc is the correct value of p[curr].
            known_values[curr] = val_bc;
            confidence++; 
        }
    }

    // After the loop, 'best' is the index of 0 with high probability.
    vector<int> ans(n + 1);
    ans[best] = 0;
    
    // Fill in the permutation
    for (int i = 1; i <= n; ++i) {
        if (i == best) continue;
        if (known_values[i] != -1) {
            ans[i] = known_values[i];
        } else {
            // If we didn't store the value (because best changed or it was early in loop)
            ans[i] = query(best, i);
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}