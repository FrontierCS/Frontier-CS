/**
 * Solution for "Geemu"
 * Implements a constructive algorithm to recover a hidden permutation.
 * The strategy is to reorder the permutation such that adjacent elements
 * have adjacent values (i.e., difference of 1).
 * We maintain a prefix p[1...len] that forms a contiguous value chain.
 * We binary search the remaining elements to find the one that extends the chain.
 * Swaps are used to keep the search range contiguous relative to the chain end.
 */
#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

// p_map[i] stores the original index of the element currently at position i
// Initially p_map[i] = i. When we swap elements at positions i and j,
// we also swap p_map[i] and p_map[j].
vector<int> p_map;
int n;

// Helper to perform swap operation
void perform_swap(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << endl;
    // Read response (always 1)
    int res;
    cin >> res;
    swap(p_map[i], p_map[j]);
}

// Helper to perform query operation
int query(int l, int r) {
    if (l > r) return 0;
    if (l == r) return 1;
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int l1, l2;
    if (!(cin >> n >> l1 >> l2)) return 0;

    p_map.resize(n + 1);
    iota(p_map.begin(), p_map.end(), 0);

    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }

    int len = 1;
    bool reversed_once = false;

    // We build the chain of values from 1 to n.
    // At step len, p[1...len] is a contiguous chain.
    // We look for a neighbor of p[len] in p[len+1...n].
    while (len < n) {
        bool has_neighbor = true;
        // Check if p[len] has a neighbor in the remaining elements
        if (!reversed_once) {
            int q_all = query(len, n);
            int q_rest = query(len + 1, n);
            // If p[len] connects to the rest, q_all should be equal to q_rest.
            // If it doesn't, q_all will be q_rest + 1.
            if (q_all != q_rest) {
                has_neighbor = false;
            }
        }

        if (!has_neighbor) {
            // We hit an endpoint (value 1 or n).
            // Reverse the current chain so the other end (which has a neighbor) becomes p[len].
            for (int i = 1; i <= len / 2; ++i) {
                perform_swap(i, len - i + 1);
            }
            reversed_once = true;
            continue;
        }

        // Binary search to find the neighbor index in [len+1, n]
        // The "head" of our chain is p[len]. We will move it around during BS.
        int L = len + 1;
        int R = n;
        int head_pos = len;

        while (L < R) {
            int M = L + (R - L) / 2;
            
            // Check if the neighbor is in the range [L, M].
            // We need to query the union of {head} and {elements in L...M}.
            // head is at head_pos. It must be adjacent to [L, M].
            // Our invariant ensures head_pos is L-1.
            
            // query(L, M) gives segments in candidates.
            // query(L-1, M) gives segments in candidates + head.
            int q_seg = query(L, M);
            int q_join = query(L - 1, M);
            
            if (q_join == q_seg) {
                // Number of segments didn't increase => head connected to something in [L, M]
                R = M;
                // head_pos is at L-1. New L is L. head_pos remains L-1. OK.
            } else {
                // Head did not connect to [L, M] => neighbor is in [M+1, R]
                // We advance L to M+1.
                // We must move head_pos to M to maintain adjacency.
                perform_swap(head_pos, M);
                head_pos = M;
                L = M + 1;
            }
        }
        
        // Now L is the index of the neighbor.
        // head_pos is at L-1.
        
        // Restore the positions:
        // We want the head (value p[len]) at index len.
        // We want the neighbor (value p[len+1]) at index len+1.
        
        // Currently head is at head_pos.
        if (head_pos != len) {
            perform_swap(head_pos, len);
            // If the neighbor was at len (unlikely/impossible given logic but for safety), track it.
            if (L == len) L = head_pos;
        }
        
        // Currently neighbor is at L.
        if (L != len + 1) {
            perform_swap(L, len + 1);
        }
        
        len++;
    }

    // Construct the result permutation
    // The element originally at p_map[i] ends up at position i (value i).
    // So P[p_map[i]] = i.
    vector<int> ans(n + 1);
    for (int i = 1; i <= n; ++i) {
        ans[p_map[i]] = i;
    }

    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}