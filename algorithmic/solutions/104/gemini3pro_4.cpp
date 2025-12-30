#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <set>

using namespace std;

struct State {
    int L, R;
    int h1, h2; // h1 is older, h2 is newer. 0: dishonest, 1: honest. -1: unknown

    bool operator<(const State& other) const {
        if (L != other.L) return L < other.L;
        if (R != other.R) return R < other.R;
        if (h1 != other.h1) return h1 < other.h1;
        return h2 < other.h2;
    }
};

int query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int x;
    cin >> x;
    return x;
}

bool guess(int a) {
    cout << "! " << a << endl;
    int y;
    cin >> y;
    return y == 1;
}

// Check if appending next_h is valid
bool isValid(int h1, int h2, int next_h) {
    if (h1 != -1 && h2 != -1 && next_h != -1) {
        if (h1 == h2 && h2 == next_h) return false;
    }
    return true;
}

void solve() {
    int n;
    cin >> n;

    vector<State> states;
    states.push_back({1, n, -1, -1});

    // Strategy: Alternate between "Known" query (on [1, n]) and "Unknown" query (Binary Search step).
    // Known query filters the history state.
    // Unknown query splits the range or reduces candidates.
    bool do_known = true; 

    while (true) {
        // Analyze current states
        set<int> candidates;
        bool has_large_range = false;
        int max_width = 0;
        State target_state = {-1, -1, -1, -1};

        for (const auto& s : states) {
            if (s.L == s.R) candidates.insert(s.L);
            else {
                has_large_range = true;
                if (s.R - s.L > max_width) {
                    max_width = s.R - s.L;
                    target_state = s;
                }
            }
        }

        // Termination condition:
        // No ranges > 1 and number of candidate students <= 2.
        if (!has_large_range && candidates.size() <= 2) {
            break;
        }

        if (do_known) {
            // Query K: [1, n]
            // Response 'n-1' implies Honest (TN, absent in range).
            // Response 'n' implies Dishonest (FP, absent in range).
            int val = query(1, n);
            int observed_h = (val == n - 1) ? 1 : 0;
            
            vector<State> next_states;
            for (auto& s : states) {
                if (isValid(s.h1, s.h2, observed_h)) {
                    next_states.push_back({s.L, s.R, s.h2, observed_h});
                }
            }
            states = next_states;
        } else {
            // Query U
            // Pick a range to target.
            int ql, qr;
            if (has_large_range) {
                ql = target_state.L;
                qr = (target_state.L + target_state.R) / 2;
            } else {
                // Pick first candidate to disambiguate
                ql = *candidates.begin();
                qr = ql;
            }

            int val = query(ql, qr);
            vector<State> next_states;
            for (auto& s : states) {
                int len = qr - ql + 1;

                // Try H = 1 (Honest)
                if (isValid(s.h1, s.h2, 1)) {
                    // Honest:
                    // val = len -> Absent NOT in [ql, qr] (TP)
                    // val = len-1 -> Absent IN [ql, qr] (TN)
                    int absent_in = -1; 
                    if (val == len) absent_in = 0;
                    else if (val == len - 1) absent_in = 1;
                    
                    if (absent_in != -1) {
                        int nL = s.L, nR = s.R;
                        int segL = ql, segR = qr;
                        if (absent_in == 1) { // Must be in [ql, qr]
                            nL = max(nL, segL);
                            nR = min(nR, segR);
                            if (nL <= nR) next_states.push_back({nL, nR, s.h2, 1});
                        } else { // Must NOT be in [ql, qr]
                            if (nL >= segL && nR <= segR) {
                                // Empty
                            } else if (nL < segL && nR > segR) {
                                // Split
                                next_states.push_back({nL, segL - 1, s.h2, 1});
                                next_states.push_back({segR + 1, nR, s.h2, 1});
                            } else if (nR <= segL || nL >= segR + 1) {
                                // Disjoint, keep all
                                next_states.push_back({nL, nR, s.h2, 1});
                            } else {
                                // Partial overlap
                                if (nL < segL) nR = min(nR, segL - 1);
                                else nL = max(nL, segR + 1);
                                if (nL <= nR) next_states.push_back({nL, nR, s.h2, 1});
                            }
                        }
                    }
                }

                // Try H = 0 (Dishonest)
                if (isValid(s.h1, s.h2, 0)) {
                    // Dishonest:
                    // val = len -> Absent IN [ql, qr] (FP)
                    // val = len-1 -> Absent NOT in [ql, qr] (FN)
                    int absent_in = -1;
                    if (val == len) absent_in = 1; 
                    else if (val == len - 1) absent_in = 0; 
                    
                    if (absent_in != -1) {
                        int nL = s.L, nR = s.R;
                        int segL = ql, segR = qr;
                        if (absent_in == 1) { // Must be in [ql, qr]
                            nL = max(nL, segL);
                            nR = min(nR, segR);
                            if (nL <= nR) next_states.push_back({nL, nR, s.h2, 0});
                        } else { // Must NOT be in [ql, qr]
                            if (nL >= segL && nR <= segR) {
                                // Empty
                            } else if (nL < segL && nR > segR) {
                                // Split
                                next_states.push_back({nL, segL - 1, s.h2, 0});
                                next_states.push_back({segR + 1, nR, s.h2, 0});
                            } else if (nR <= segL || nL >= segR + 1) {
                                // Disjoint
                                next_states.push_back({nL, nR, s.h2, 0});
                            } else {
                                // Partial overlap
                                if (nL < segL) nR = min(nR, segL - 1);
                                else nL = max(nL, segR + 1);
                                if (nL <= nR) next_states.push_back({nL, nR, s.h2, 0});
                            }
                        }
                    }
                }
            }
            states = next_states;
        }

        // Deduplicate states
        if (!states.empty()) {
            sort(states.begin(), states.end());
            vector<State> unique_states;
            unique_states.push_back(states[0]);
            for (size_t i = 1; i < states.size(); ++i) {
                State& last = unique_states.back();
                if (states[i].L == last.L && states[i].R == last.R && states[i].h1 == last.h1 && states[i].h2 == last.h2) continue;
                unique_states.push_back(states[i]);
            }
            states = unique_states;
        }
        
        do_known = !do_known;
    }

    // Collect candidates
    set<int> final_candidates;
    for (const auto& s : states) {
        if (s.L == s.R) final_candidates.insert(s.L);
    }
    
    vector<int> cands(final_candidates.begin(), final_candidates.end());
    if (cands.empty()) {
        guess(1);
    } else {
        if (guess(cands[0])) return;
        if (cands.size() > 1) guess(cands[1]);
    }
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
            cout << "#" << endl;
        }
    }
    return 0;
}