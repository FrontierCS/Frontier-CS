#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to represent a range of students and their possible state history
// mask bits: 0: H, 1: HH, 2: D, 3: DD
struct Block {
    int l, r;
    int mask;
};

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    vector<Block> blocks;
    // Initially all students are candidates, and any history (H/D etc.) is possible start
    // Mask 1111 (binary) = 15 represents {H, HH, D, DD}
    blocks.push_back({1, n, 15}); 

    auto count_active = [&](const vector<Block>& blks) {
        int cnt = 0;
        for(auto& b : blks) cnt += (b.r - b.l + 1);
        return cnt;
    };

    while (true) {
        int active = count_active(blocks);
        
        // If we have narrowed down to at most 2 candidates, we can guess them.
        if (active <= 2) {
            vector<int> candidates;
            for(auto& b : blocks) {
                for(int i=b.l; i<=b.r; ++i) candidates.push_back(i);
            }
            
            for (int x : candidates) {
                cout << "! " << x << endl;
                int res;
                cin >> res;
                if (res == 1) {
                    cout << "#" << endl;
                    return; 
                }
                // If incorrect, try next candidate
            }
            // Should be solved by now given constraints
            cout << "#" << endl;
            return;
        }

        // Strategy: Split the set of active candidates roughly in half.
        // Candidates in the query range will follow one set of state transitions (based on 'IN' hypothesis),
        // candidates outside will follow the other.
        int target = active / 2;
        int current = 0;
        int split_k = -1;
        
        for (int i = 0; i < blocks.size(); ++i) {
            int sz = blocks[i].r - blocks[i].l + 1;
            if (current + sz >= target) {
                int take = target - current;
                if (take < 1) take = 1; 
                split_k = blocks[i].l + take - 1;
                break;
            }
            current += sz;
        }
        
        // Ensure valid query range
        if (split_k < 1) split_k = 1;
        if (split_k >= n) split_k = n - 1; 

        cout << "? 1 " << split_k << endl;
        int response;
        cin >> response;
        
        // Interpretation of response:
        // Range length len = split_k.
        // If response == len, the claim is "Everyone in range is present" => Claim OUT.
        // If response == len - 1, the claim is "One student in range is absent" => Claim IN.
        bool claim_in = (response == split_k - 1);
        
        vector<Block> next_blocks;
        
        auto process = [&](int l, int r, int mask, bool is_in_range) {
            // is_in_range: Is the candidate i inside [1, split_k]?
            // Truth regarding location: 
            //   If is_in_range, Truth = IN.
            //   If !is_in_range, Truth = OUT.
            
            // Deduction of Query Honesty for candidate i:
            //   If Truth == Claim, implies query was Honest.
            //   If Truth != Claim, implies query was Dishonest.
            
            // Logic table:
            // is_in_range | claim_in | Match? | Implies
            // true        | true     | Yes    | Honest
            // true        | false    | No     | Dishonest
            // false       | true     | No     | Dishonest
            // false       | false    | Yes    | Honest
            
            bool implies_honest = (is_in_range == claim_in);
            
            int new_mask = 0;
            // Transitions:
            // H=1 (bit 0), HH=2 (bit 1), D=4 (bit 2), DD=8 (bit 3)
            
            if (implies_honest) {
                // Honest Transition
                // H -> HH
                if (mask & 1) new_mask |= 2;
                // HH -> Invalid (Cannot be Honest 3 times)
                // D -> H
                if (mask & 4) new_mask |= 1;
                // DD -> H
                if (mask & 8) new_mask |= 1;
            } else {
                // Dishonest Transition
                // H -> D
                if (mask & 1) new_mask |= 4;
                // HH -> D
                if (mask & 2) new_mask |= 4;
                // D -> DD
                if (mask & 4) new_mask |= 8;
                // DD -> Invalid (Cannot be Dishonest 3 times)
            }
            
            if (new_mask) {
                next_blocks.push_back({l, r, new_mask});
            }
        };

        for (auto& b : blocks) {
            if (b.r <= split_k) {
                process(b.l, b.r, b.mask, true);
            } else if (b.l > split_k) {
                process(b.l, b.r, b.mask, false);
            } else {
                process(b.l, split_k, b.mask, true);
                process(split_k + 1, b.r, b.mask, false);
            }
        }
        
        // Merge adjacent blocks with same mask
        if (!next_blocks.empty()) {
            vector<Block> merged;
            merged.push_back(next_blocks[0]);
            for(size_t i=1; i<next_blocks.size(); ++i) {
                if (next_blocks[i].mask == merged.back().mask && next_blocks[i].l == merged.back().r + 1) {
                    merged.back().r = next_blocks[i].r;
                } else {
                    merged.push_back(next_blocks[i]);
                }
            }
            blocks = merged;
        } else {
            // Should not happen, implies no candidate consistent
            return;
        }
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