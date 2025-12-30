/*
    Problem: Geemu
    Algorithm: Interactive Sorting via Chain Reconstruction
    
    We reconstruct the value chain (Hamiltonian path of the value graph where edges represent |u-v|=1).
    Since we can detect value adjacency of two indices by bringing them together and querying,
    we can start with an arbitrary element and extend the chain in both directions.
    To efficiently find the next element in the chain among the unused elements, we use binary search
    aided by the ability to move elements into contiguous blocks.
*/

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <deque>

using namespace std;

int n, l1, l2;
vector<int> at_pos; // at_pos[p] = original_index currently at position p
vector<int> pos_of; // pos_of[idx] = current position of original_index idx

// Wrapper for Query 1: Number of value-contiguous segments
int query(int l, int r) {
    if (l >= r) return 1; // Single element or empty range is always 1 segment
    cout << "1 " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

// Wrapper for Query 2: Swap
void do_swap(int p1, int p2) {
    if (p1 == p2) return;
    cout << "2 " << p1 << " " << p2 << endl;
    int res;
    cin >> res;
    // Update tracking
    int id1 = at_pos[p1];
    int id2 = at_pos[p2];
    swap(at_pos[p1], at_pos[p2]);
    pos_of[id1] = p2;
    pos_of[id2] = p1;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> l1 >> l2)) return 0;

    // Base case n=1
    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }

    // Initialize tracking arrays
    at_pos.resize(n + 1);
    pos_of.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        at_pos[i] = i;
        pos_of[i] = i;
    }

    deque<int> chain;
    // Start with the element originally at index 1
    int start_node = at_pos[1]; 
    chain.push_back(start_node);
    
    // We maintain the set of "unused" (not yet in chain) elements in a contiguous suffix of the array.
    // Initially, elements at positions 2..n are unused. The element at pos 1 is in the chain.
    int unused_start = 2;
    
    // Direction flag: false = extending from back of deque, true = extending from front
    bool reverse_mode = false;

    while (unused_start <= n) {
        // Get the current tip of the chain we are trying to extend
        int tip = reverse_mode ? chain.front() : chain.back();
        
        // Ensure tip is physically adjacent to the unused block [unused_start, n].
        // We place tip at unused_start - 1.
        int tip_p = pos_of[tip];
        if (tip_p != unused_start - 1) {
            do_swap(tip_p, unused_start - 1);
        }
        
        // Check if there is any neighbor of 'tip' in the unused set.
        // We query [unused_start-1, n] (includes tip) and [unused_start, n] (excludes tip).
        // If the number of segments is equal, it means 'tip' merged with some segment in unused,
        // implying a connection (value adjacency) exists.
        int q_connected = query(unused_start - 1, n);
        int q_isolated = query(unused_start, n);
        
        if (q_connected == q_isolated) {
            // Neighbor exists in unused [unused_start, n]. Find it using binary search.
            int l = unused_start;
            int r = n;
            // Invariant: tip is at l-1, and we are searching in [l, r]
            
            while (l < r) {
                int mid = l + (r - l) / 2;
                // Check prefix [l, mid]. Tip is at l-1, so checking [l-1, mid] vs [l, mid].
                int qc = query(l - 1, mid);
                int qi = query(l, mid);
                
                if (qc == qi) {
                    // Neighbor is in [l, mid].
                    r = mid;
                    // tip stays at l-1, which is correct for next iteration
                } else {
                    // Neighbor is in [mid+1, r].
                    // We need to move tip to be adjacent to [mid+1, r].
                    // Current tip is at l-1. Target position is mid.
                    do_swap(l - 1, mid);
                    l = mid + 1;
                    // Now tip is at mid, which is l-1. Correct.
                }
            }
            
            // Found neighbor at position l
            int neighbor = at_pos[l];
            
            // We need to move the found neighbor to 'unused_start' (to mark it as used/next in chain)
            // and ensure 'tip' is moved out of the way (to 'unused_start-1').
            // The binary search scrambled the [unused_start-1, n] block, but we know
            // tip is at l-1 and neighbor is at l.
            
            // Restore tip to unused_start-1
            do_swap(pos_of[tip], unused_start - 1);
            // Move neighbor to unused_start
            do_swap(pos_of[neighbor], unused_start);
            
            // Add neighbor to chain
            if (reverse_mode) chain.push_front(neighbor);
            else chain.push_back(neighbor);
            
            // Shrink unused range
            unused_start++;
            
        } else {
            // No neighbor in unused. 'tip' is an endpoint of the value chain (1 or n).
            // Switch to extending from the other end of the chain.
            if (!reverse_mode) {
                reverse_mode = true;
            } else {
                // If we are already in reverse mode and hit a dead end, we are done 
                // (should happen when unused_start > n, but just in case)
                break;
            }
        }
    }
    
    // Assign values based on chain order.
    // chain[0] is one end (1 or n), chain[n-1] is the other.
    // Since we only need one valid p, we assume chain corresponds to 1, 2, ..., n.
    vector<int> val(n + 1);
    for (int i = 0; i < n; ++i) {
        val[chain[i]] = i + 1;
    }
    
    // Output the permutation currently in the array.
    // The problem asks for "final p", so we report values based on what is currently at each position.
    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << " " << val[at_pos[i]];
    }
    cout << endl;

    return 0;
}