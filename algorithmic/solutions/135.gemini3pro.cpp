#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <numeric>

using namespace std;

struct QueryResult {
    int r;
    vector<pair<int, int>> pairs;
};

QueryResult ask(int u, int x, int y) {
    cout << "? " << u << " " << x << " " << y << endl;
    int r;
    cin >> r;
    vector<pair<int, int>> pairs(r);
    for (int i = 0; i < r; ++i) {
        cin >> pairs[i].first >> pairs[i].second;
        if (pairs[i].first > pairs[i].second) swap(pairs[i].first, pairs[i].second);
    }
    return {r, pairs};
}

// Check if pair {a, b} is in the result.
bool has_pair(const QueryResult& res, int a, int b) {
    if (a > b) swap(a, b);
    for (auto& p : res.pairs) {
        if (p.first == a && p.second == b) return true;
    }
    return false;
}

// Returns -1 if u is closer to a, 1 if closer to b, 0 if ambiguous/tie.
// We assume we want to split based on a vs b.
// If {a, b} is returned as closest, it means u is far from both (relatively), 
// but in our binary search logic we usually ensure u is somewhat between a and b.
// However, if {a, b} is returned, we can't decide. But with "Opposite" strategy, {a, b} won't be returned.
int compare_dist(int u, int a, int b) {
    QueryResult res = ask(u, a, b);
    bool ua = has_pair(res, u, a);
    bool ub = has_pair(res, u, b);
    
    if (ua && !ub) return -1;
    if (!ua && ub) return 1;
    return 0; // Tie or {a,b} is closest
}

int main() {
    int k_limit, n;
    if (!(cin >> k_limit >> n)) return 0;

    vector<int> S;
    S.push_back(0);
    S.push_back(1);
    S.push_back(2);

    vector<int> to_insert;
    for (int i = 3; i < n; ++i) to_insert.push_back(i);

    // To prevent predictable patterns, though not strictly necessary as doors are random.
    // Random shuffle not needed per problem statement.

    for (int u : to_insert) {
        int len = S.size();
        
        // For small size, linear scan is safer and cheap enough
        if (len < 6) {
            bool inserted = false;
            for (int i = 0; i < len; ++i) {
                int a = S[i];
                int b = S[(i + 1) % len];
                QueryResult res = ask(u, a, b);
                // If {a, b} is NOT the closest pair, then u is "between" a and b (on the short arc)
                if (!has_pair(res, a, b)) {
                    S.insert(S.begin() + i + 1, u);
                    inserted = true;
                    break;
                }
            }
            // Should always be inserted
            continue;
        }

        // Binary Search Strategy
        // Phase 1: Global split using opposite vertices
        // Pivot at index 0 and index len/2
        int p1_idx = 0;
        int p2_idx = len / 2;
        int P = S[p1_idx];
        int Q = S[p2_idx];

        int dir = compare_dist(u, P, Q);
        
        long long low, high;
        
        // Define range of SLOTS. Slot i is between S[i] and S[i+1].
        // We work with unwrapped indices.
        // Range covers roughly half the circle centered at the winner.
        // Half circle is len/2 slots.
        // We add some padding to be safe.
        
        if (dir == -1) { // Closer to P (index 0)
            // Range centered at 0: roughly [-len/4, len/4]
            low = -len / 4 - 1;
            high = len / 4 + 1;
        } else { // Closer to Q (index len/2) or tie
            // Range centered at len/2: roughly [len/4, 3*len/4]
            low = len / 4 - 1;
            high = 3 * len / 4 + 1;
        }

        // Phase 2: Binary Search
        while (high - low > 0) {
            long long mid = (low + high) / 2; 
            // We want to check if u is in slots [low, mid] or [mid+1, high]
            // The boundary is vertex S[mid+1] (using unwrapped indexing)
            
            // To split at vertex S[mid+1], we pick two anchors symmetric around it.
            // A good choice is the ends of the current range, or slightly wider.
            // Let's use low and high+1 (indices of vertices around the slot range).
            // Vertex corresponding to start of slot `low` is S[low].
            // Vertex corresponding to end of slot `high` is S[high+1].
            
            // To avoid picking same vertex if range is small, just use computed indices.
            int idx_L = (low % len + len) % len;
            int idx_R = ((high + 1) % len + len) % len;

            if (idx_L == idx_R) {
                // Should not happen if logic is correct and len >= 6
                // Fallback to shrink
                high = mid; 
                continue;
            }

            int d = compare_dist(u, S[idx_L], S[idx_R]);
            
            if (d == -1) {
                // Closer to Left anchor -> Left half
                high = mid;
            } else {
                // Closer to Right anchor -> Right half
                // If tie, can go either way, but typically means close to midpoint.
                // Let's bias right to ensure progress or consistency.
                low = mid + 1;
            }
        }
        
        // Insert at slot `low`. 
        // Slot `low` corresponds to insertion index `low + 1`.
        // Normalize index
        long long insert_pos = (low + 1);
        int final_idx = (insert_pos % len + len) % len;
        
        // If final_idx is 0, it means insert before S[0] (or after S[len-1]).
        // Wait, slot len-1 is (S[len-1], S[0]). Insert index is len.
        // Slot 0 is (S[0], S[1]). Insert index is 1.
        // Slot -1 is (S[len-1], S[0]). Insert index is 0 (equivalent to len).
        // Let's use `insert` logic. vector::insert inserts before position.
        // If we want to insert after S[i], we insert at i+1.
        // If i+1 == len, it appends.
        // If i+1 == 0 (wrapped), it inserts at 0.
        
        // We need to map `insert_pos` carefully.
        // S[low] ... u ... S[low+1]
        // unwrapped index `low`. u is after `low`.
        // So we insert at `low + 1`.
        // We need to find the correct index in 0..len.
        // unwrapped `low+1` maps to `(low+1)%len`.
        // But if `(low+1)` is `len`, we append.
        // Actually, vector indices are 0..len-1.
        // Inserting at `k` shifts `k`..`end` to right.
        // We want u to be at index `final_idx`.
        // If `low` corresponds to the last element (modulo), we append.
        // Let's calculate offset from 0.
        // S is rotated. But we maintain linear vector.
        // `low` is relative to current `S` indexing.
        // So simply:
        
        int idx = (low + 1) % len;
        if (idx < 0) idx += len;
        
        // Special case: if we are appending to the end (logically between S[len-1] and S[0]),
        // index 0 or len works. Let's use index `idx`.
        // If idx is 0, we insert at beginning.
        // If idx is not 0, insert at idx.
        // Wait, if slot is `len-1`, `low` maps to `len-1`. `low+1` maps to `len` (which is 0 mod len).
        // We should insert at `len`. But `S.insert` at `S.end()` is same as `S.begin() + len`.
        // But if we insert at 0, order becomes u, S[0], S[1]...
        // Which is effectively ..., S[len-1], u, S[0], ...
        // So inserting at 0 is correct for slot `len-1`.
        
        S.insert(S.begin() + idx, u);
    }

    cout << "!";
    for (int x : S) cout << " " << x;
    cout << endl;

    return 0;
}