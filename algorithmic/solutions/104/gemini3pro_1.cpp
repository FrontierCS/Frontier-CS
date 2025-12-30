#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>
#include <iomanip>

using namespace std;

// Constants and types
const double W = 1.61803398875; // Golden ratio phi
// States: 
// 0: Last D (count 1)
// 1: Last DD (count 2)
// 2: Last H (count 1)
// 3: Last HH (count 2)
// 4: START

struct Candidate {
    int id;
    int state; // 0-4
};

// Update state based on assumed honesty h (0 for D, 1 for H)
// Returns -1 if invalid/die
int next_state(int current, int h) {
    if (current == 4) { // START
        return (h == 1) ? 2 : 0;
    }
    if (current == 0) { // D
        return (h == 1) ? 2 : 1;
    }
    if (current == 1) { // DD
        return (h == 1) ? 2 : -1;
    }
    if (current == 2) { // H
        return (h == 1) ? 3 : 0;
    }
    if (current == 3) { // HH
        return (h == 1) ? -1 : 0;
    }
    return -1;
}

void solve() {
    int n;
    cin >> n;
    
    vector<Candidate> candidates;
    candidates.reserve(n);
    for (int i = 1; i <= n; ++i) {
        candidates.push_back({i, 4});
    }

    while (candidates.size() > 2) {
        // Special case for step 0 (all START)
        bool all_start = true;
        for (const auto& c : candidates) if (c.state != 4) { all_start = false; break; }
        
        int best_l = -1, best_r = -1;

        if (all_start) {
            best_l = candidates[0].id;
            best_r = candidates[candidates.size() / 2 - 1].id;
        } else {
            double total_h = 0, total_d = 0;
            vector<double> diffs;
            diffs.reserve(candidates.size());

            for (const auto& c : candidates) {
                double vh = 0, vd = 0;
                // Weights derived from potential function analysis
                if (c.state == 0) { vh = W; vd = 1; }
                else if (c.state == 1) { vh = W; vd = 0; }
                else if (c.state == 2) { vh = 1; vd = W; }
                else if (c.state == 3) { vh = 0; vd = W; }
                else if (c.state == 4) { vh = W; vd = W; }
                
                total_h += vh;
                total_d += vd;
                diffs.push_back(vh - vd);
            }

            double target = (total_h - total_d) / 2.0;
            
            // Find subarray with sum closest to target
            // We store prefix sums in a set to find optimal range [i, j]
            // We want (Prefix[j] - Prefix[i-1]) approx Target
            
            set<pair<double, int>> s;
            s.insert({0.0, -1});
            
            double current_sum = 0;
            double best_err = 1e18;
            int best_start = -1, best_end = -1;

            for (int i = 0; i < (int)diffs.size(); ++i) {
                current_sum += diffs[i];
                double needed = current_sum - target;
                
                auto it = s.lower_bound({needed, -100000});
                
                // Check iterator it
                if (it != s.end()) {
                    double err = abs((current_sum - it->first) - target);
                    if (err < best_err) {
                        best_err = err;
                        best_start = it->second + 1;
                        best_end = i;
                    }
                }
                // Check iterator before it
                if (it != s.begin()) {
                    auto it2 = prev(it);
                    double err = abs((current_sum - it2->first) - target);
                    if (err < best_err) {
                        best_err = err;
                        best_start = it2->second + 1;
                        best_end = i;
                    }
                }
                s.insert({current_sum, i});
            }
            
            // Fallback if empty interval chosen (could happen if target ~ 0 and best match is len 0)
            if (best_start > best_end) {
                best_start = 0;
                best_end = candidates.size() / 2 - 1;
            }
            
            best_l = candidates[best_start].id;
            best_r = candidates[best_end].id;
        }

        cout << "? " << best_l << " " << best_r << endl;
        int x;
        cin >> x;

        vector<Candidate> next_cands;
        next_cands.reserve(candidates.size());
        int len = best_r - best_l + 1;
        
        for (const auto& c : candidates) {
            int input_h = -1; // 0 for D, 1 for H
            if (c.id >= best_l && c.id <= best_r) {
                // In range logic
                // If A in range, count is len-1. Honest -> len-1. Dishonest -> len.
                if (x == len - 1) input_h = 1;
                else if (x == len) input_h = 0;
            } else {
                // Out of range logic
                // If A out of range, count is len. Honest -> len. Dishonest -> len-1.
                if (x == len) input_h = 1;
                else if (x == len - 1) input_h = 0;
            }
            
            if (input_h != -1) {
                int ns = next_state(c.state, input_h);
                if (ns != -1) {
                    next_cands.push_back({c.id, ns});
                }
            }
        }
        candidates = next_cands;
    }

    for (const auto& c : candidates) {
        cout << "! " << c.id << endl;
        int res;
        cin >> res;
        if (res == 1) break;
    }
    cout << "#" << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}