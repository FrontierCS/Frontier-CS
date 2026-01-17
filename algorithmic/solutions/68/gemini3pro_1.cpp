#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>
#include <chrono>

using namespace std;

// Function to handle each test case
void solve() {
    int n;
    if (!(cin >> n)) return;
    
    // Initial set of pens P. We don't know their ink values.
    vector<int> P(n);
    iota(P.begin(), P.end(), 0);
    
    // Shuffle P to ensure random matchups, which is crucial for the heuristic to work well.
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    shuffle(P.begin(), P.end(), std::default_random_engine(seed));
    
    // Set H will store "heavy" pens (candidates that have survived at least one round).
    vector<int> H;
    
    // Helper lambda for querying a pen
    auto query = [&](int id) -> int {
        cout << "0 " << id << endl;
        int res;
        cin >> res;
        return res;
    };
    
    // We continue until we have exactly 2 pens left.
    // The strategy is to eliminate pens that run out of ink (return 0).
    // We prioritize checking unknown pens (from P) against known survivors (from H) 
    // to minimize ink consumption on the survivors.
    while (P.size() + H.size() > 2) {
        if (P.empty()) {
            // Only verified pens left, we must pit them against each other.
            // This is the "endgame" where survivors battle.
            int u = H.back(); H.pop_back();
            int v = H.back(); H.pop_back();
            
            if (query(u) == 0) {
                // u is empty, remove u. v survives and returns to H.
                H.push_back(v);
            } else {
                // u has ink. Check v.
                if (query(v) == 0) {
                    // v is empty, remove v. u survives and returns to H.
                    H.push_back(u);
                } else {
                    // Both have ink. Both return to H.
                    H.push_back(u);
                    H.push_back(v);
                }
            }
        } else {
            // Pick a challenger u from P
            int u = P.back(); P.pop_back();
            
            if (H.empty()) {
                // No gatekeepers in H, so pick another challenger v from P
                int v = P.back(); P.pop_back();
                
                if (query(u) == 0) {
                    // u failed. v returns to P (untouched/unverified)
                    P.push_back(v);
                } else {
                    // u passed. Check v.
                    if (query(v) == 0) {
                        // v failed. u promoted to H
                        H.push_back(u);
                    } else {
                        // Both passed. Both promoted to H
                        H.push_back(u);
                        H.push_back(v);
                    }
                }
            } else {
                // Pick a gatekeeper v from H
                int v = H.back(); H.pop_back();
                
                // Query u first. u is more likely to be 0/small.
                if (query(u) == 0) {
                    // u failed. v saved (untouched) and returns to H
                    H.push_back(v);
                } else {
                    // u passed. Now we must risk v.
                    if (query(v) == 0) {
                        // v died. u replaces v in H
                        H.push_back(u);
                    } else {
                        // Both survived. Both in H.
                        H.push_back(u);
                        H.push_back(v);
                    }
                }
            }
        }
    }
    
    // Gather the remaining 2 pens
    vector<int> res;
    res.insert(res.end(), P.begin(), P.end());
    res.insert(res.end(), H.begin(), H.end());
    
    // Output result
    cout << "1 " << res[0] << " " << res[1] << endl;
}

int main() {
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