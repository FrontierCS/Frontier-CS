#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

struct Candidate {
    int id;
    int state; 
    // State encoding:
    // 0: LL (history: Lie, Lie)
    // 1: LT (history: Lie, Truth)
    // 2: TL (history: Truth, Lie)
    // 3: TT (history: Truth, Truth)
    // 4: L (history: Lie, length 1)
    // 5: T (history: Truth, length 1)
    // 6: Empty (start)
};

// Returns allowed next moves: 0 for L, 1 for T
// Constraint: No 3 consecutive same answers
vector<int> get_allowed(int state) {
    if (state == 6) return {0, 1};
    if (state == 5) return {0, 1}; // T -> can be L (TL) or T (TT)
    if (state == 4) return {0, 1}; // L -> can be L (LL) or T (LT)
    if (state == 3) return {0};    // TT -> must be L
    if (state == 2) return {0, 1}; // TL -> L or T
    if (state == 1) return {0, 1}; // LT -> L or T
    if (state == 0) return {1};    // LL -> must be T
    return {};
}

int next_state(int current, int move) {
    // move: 0 for L, 1 for T
    if (current == 6) return (move == 0) ? 4 : 5;
    if (current == 5) return (move == 0) ? 2 : 3;
    if (current == 4) return (move == 0) ? 0 : 1;
    // For states 0-3, shift and append
    // LL(0)->00, LT(1)->01, TL(2)->10, TT(3)->11
    // New state is (old & 1) << 1 | move
    return ((current & 1) << 1) | move;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    vector<Candidate> candidates;
    candidates.reserve(4 * n);
    for (int i = 1; i <= n; ++i) {
        candidates.push_back({i, 6});
    }

    while (true) {
        // Count unique indices
        int unique_count = 0;
        if (!candidates.empty()) {
            unique_count = 1;
            for (size_t i = 1; i < candidates.size(); ++i) {
                if (candidates[i].id != candidates[i-1].id) {
                    unique_count++;
                }
            }
        }

        if (unique_count <= 2) {
            vector<int> final_ids;
            if (!candidates.empty()) {
                final_ids.push_back(candidates[0].id);
                for (size_t i = 1; i < candidates.size(); ++i) {
                    if (candidates[i].id != candidates[i-1].id) {
                        final_ids.push_back(candidates[i].id);
                    }
                }
            }
            
            for (int id : final_ids) {
                cout << "! " << id << endl;
                int res;
                cin >> res;
                if (res == 1) {
                    cout << "#" << endl;
                    return; 
                }
            }
            // Should not be reached if solution exists and logic is correct
            cout << "#" << endl;
            return; 
        }

        // Pass 1: Calculate total D (difference between ForceT and ForceL) and W (total weight)
        long long D_tot = 0;
        long long W_tot = candidates.size();
        
        for (const auto& c : candidates) {
            vector<int> moves = get_allowed(c.state);
            bool forceT = false;
            bool forceL = false;
            if (moves.size() == 1) {
                if (moves[0] == 1) forceT = true;
                else forceL = true;
            }
            if (forceT) D_tot++;
            if (forceL) D_tot--;
        }

        // Pass 2: Find best split point x to query [1, x]
        // We want to minimize the imbalance of potential future set sizes.
        int best_x = -1;
        long long current_D = 0;
        long long current_W = 0;
        
        long long min_score_D = -1;
        long long min_score_W = -1;

        for (size_t i = 0; i < candidates.size(); ) {
            int curr_id = candidates[i].id;
            // Process all candidates with same ID
            while (i < candidates.size() && candidates[i].id == curr_id) {
                const auto& c = candidates[i];
                vector<int> moves = get_allowed(c.state);
                bool forceT = false;
                bool forceL = false;
                if (moves.size() == 1) {
                    if (moves[0] == 1) forceT = true;
                    else forceL = true;
                }
                if (forceT) current_D++;
                if (forceL) current_D--;
                current_W++;
                i++;
            }
            
            // Score based on balancing D and W
            // Ideal split has current_D approx D_tot/2 and current_W approx W_tot/2
            long long score_D = abs(2 * current_D - D_tot);
            long long score_W = abs(2 * current_W - W_tot);
            
            if (best_x == -1 || score_D < min_score_D || (score_D == min_score_D && score_W < min_score_W)) {
                min_score_D = score_D;
                min_score_W = score_W;
                best_x = curr_id;
            }
        }
        
        cout << "? 1 " << best_x << endl;
        int ans;
        cin >> ans;
        
        int r = best_x;
        int l = 1;
        int base = r - l; 
        // Responses:
        // Truth: if in range -> base (r-l). if out -> base + 1 (r-l+1).
        // Lie: if in range -> base + 1. if out -> base.
        
        bool is_low = (ans == base); 
        // is_low True means: (T and In) or (L and !In)
        // is_low False (High) means: (T and !In) or (L and In)
        
        vector<Candidate> next_candidates;
        next_candidates.reserve(candidates.size());
        
        for (const auto& c : candidates) {
            bool in_range = (c.id <= best_x);
            vector<int> moves = get_allowed(c.state);
            for (int m : moves) {
                // m=1 (T), m=0 (L)
                bool consistent = false;
                if (is_low) {
                    if ((m == 1 && in_range) || (m == 0 && !in_range)) consistent = true;
                } else {
                    if ((m == 1 && !in_range) || (m == 0 && in_range)) consistent = true;
                }
                
                if (consistent) {
                    next_candidates.push_back({c.id, next_state(c.state, m)});
                }
            }
        }
        
        candidates = move(next_candidates);
    }
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