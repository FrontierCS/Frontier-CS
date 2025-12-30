#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Base 4 representation: 5 digits needed for 1000 (4^5 = 1024)
const int NUM_DIGITS = 5;

// Convert number to base 4 digits
vector<int> to_base4(int n) {
    vector<int> digits(NUM_DIGITS);
    for (int i = 0; i < NUM_DIGITS; ++i) {
        digits[i] = n % 4;
        n /= 4;
    }
    return digits;
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    // We plan to use 29 robots:
    // Robots 0-19: Base 4 digits. 5 positions * 4 values = 20 robots.
    // Robots 20-24: Sum of digits mod 5. 5 robots.
    // Robots 25-28: Sum of digits mod 4. 4 robots.
    
    // Construct the queries
    vector<vector<int>> robots(29);
    
    for (int x = 0; x < 1000; ++x) {
        vector<int> d = to_base4(x);
        int sum_d = 0;
        for (int v : d) sum_d += v;
        
        // Base 4 queries
        for (int i = 0; i < NUM_DIGITS; ++i) {
            // Robot for digit i having value d[i]
            int robot_idx = i * 4 + d[i];
            robots[robot_idx].push_back(x + 1);
        }
        
        // Sum mod 5 queries
        int rem5 = sum_d % 5;
        robots[20 + rem5].push_back(x + 1);
        
        // Sum mod 4 queries
        int rem4 = sum_d % 4;
        robots[25 + rem4].push_back(x + 1);
    }
    
    // Send queries
    for (int i = 0; i < 29; ++i) {
        cout << "? " << robots[i].size();
        for (int pos : robots[i]) {
            cout << " " << pos;
        }
        cout << endl;
    }
    cout.flush(); // Ensure queries are sent
    
    // Get responses
    cout << "@" << endl;
    // cout.flush() is automatic with endl usually, but explicit flush is good practice if not using endl
    
    int L;
    cin >> L;
    vector<int> responses(L);
    for (int i = 0; i < L; ++i) {
        cin >> responses[i];
    }
    
    // Decode
    // 1. Identify possible values for each digit
    vector<vector<int>> possible_digits(NUM_DIGITS);
    for (int i = 0; i < NUM_DIGITS; ++i) {
        for (int v = 0; v < 4; ++v) {
            // Check if robot i*4 + v found anything
            if (responses[i * 4 + v]) {
                possible_digits[i].push_back(v);
            }
        }
    }
    
    // 2. Identify possible sums mod 5 and mod 4
    vector<int> present_mod5, present_mod4;
    for (int r = 0; r < 5; ++r) {
        if (responses[20 + r]) present_mod5.push_back(r);
    }
    for (int r = 0; r < 4; ++r) {
        if (responses[25 + r]) present_mod4.push_back(r);
    }
    
    // 3. Generate candidate numbers
    // A number is a candidate if for all i, its i-th digit is in possible_digits[i]
    vector<int> candidates;
    candidates.push_back(0); // Initial seed
    
    for (int i = 0; i < NUM_DIGITS; ++i) {
        vector<int> next_candidates;
        // possible_digits[i] should not be empty
        for (int cand : candidates) {
            for (int val : possible_digits[i]) {
                // val * 4^i
                next_candidates.push_back(cand + val * (1 << (2 * i))); 
            }
        }
        candidates = next_candidates;
    }
    
    // Filter candidates to valid range [0, 999]
    vector<int> valid_candidates;
    for (int c : candidates) {
        if (c < 1000) valid_candidates.push_back(c);
    }
    candidates = valid_candidates;
    
    // 4. Find the pair {A, B}
    // Iterate over all pairs of candidates
    int bestA = 1, bestB = 1;
    bool found = false;
    
    int nC = candidates.size();
    for (int i = 0; i < nC; ++i) {
        for (int j = i; j < nC; ++j) {
            int u = candidates[i];
            int v = candidates[j];
            
            // Check Base 4 coverage
            // The union of digits of u and v must match possible_digits exactly
            bool digits_ok = true;
            vector<int> du = to_base4(u);
            vector<int> dv = to_base4(v);
            
            int sum_u = 0, sum_v = 0;
            for (int k = 0; k < NUM_DIGITS; ++k) {
                sum_u += du[k];
                sum_v += dv[k];
                
                // The set {du[k], dv[k]} must equal possible_digits[k]
                // possible_digits[k] size is 1 or 2
                
                if (possible_digits[k].size() == 1) {
                    // Both must be the single value
                    if (du[k] != possible_digits[k][0] || dv[k] != possible_digits[k][0]) {
                        digits_ok = false; break;
                    }
                } else {
                    // One must be first, other second (order doesn't matter)
                    int p0 = possible_digits[k][0];
                    int p1 = possible_digits[k][1];
                    if (!((du[k] == p0 && dv[k] == p1) || (du[k] == p1 && dv[k] == p0))) {
                        digits_ok = false; break;
                    }
                }
            }
            if (!digits_ok) continue;
            
            // Check Mod 5 consistency
            set<int> obs_mod5;
            obs_mod5.insert(sum_u % 5);
            obs_mod5.insert(sum_v % 5);
            // Size must match number of observed mod5 responses
            if (obs_mod5.size() != present_mod5.size()) continue;
            // Values must match
            bool mod5_ok = true;
            for (int pm : present_mod5) {
                if (obs_mod5.find(pm) == obs_mod5.end()) {
                    mod5_ok = false; break;
                }
            }
            if (!mod5_ok) continue;
            
            // Check Mod 4 consistency
            set<int> obs_mod4;
            obs_mod4.insert(sum_u % 4);
            obs_mod4.insert(sum_v % 4);
            if (obs_mod4.size() != present_mod4.size()) continue;
            bool mod4_ok = true;
            for (int pm : present_mod4) {
                if (obs_mod4.find(pm) == obs_mod4.end()) {
                    mod4_ok = false; break;
                }
            }
            if (!mod4_ok) continue;
            
            // Found a consistent pair
            bestA = u + 1;
            bestB = v + 1;
            found = true;
            break;
        }
        if (found) break;
    }
    
    cout << "! " << bestA << " " << bestB << endl;
    
    return 0;
}