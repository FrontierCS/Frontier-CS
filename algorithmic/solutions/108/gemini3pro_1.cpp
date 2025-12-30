#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

int N, n, m;

// Function to perform a query
int query(int ring, int dir) {
    cout << "? " << ring << " " << dir << endl;
    int ans;
    cin >> ans;
    return ans;
}

// Keep track of current offsets relative to initial position
vector<int> current_offset;

// Helper to rotate a ring by k steps
// k > 0 clockwise, k < 0 anti-clockwise
// Updates current_offset
int rotate_ring(int ring, int k) {
    int final_res = -1;
    if (k == 0) return -1; // Should not happen or handle gracefully if needed, but we typically query after rot
    int steps = abs(k);
    int dir = (k > 0) ? 1 : -1;
    for (int i = 0; i < steps; ++i) {
        final_res = query(ring, dir);
    }
    current_offset[ring] = (current_offset[ring] + k) % N;
    if (current_offset[ring] < 0) current_offset[ring] += N;
    return final_res;
}

int main() {
    if (!(cin >> n >> m)) return 0;
    N = n * m;
    current_offset.resize(n, 0);

    // Initial unblocked count (though we might not know it without a query, 
    // but we can just do a dummy query or assume the first op gives us info)
    // We'll just start processing.
    
    // Target: Align all rings 1..n-1 to ring 0.
    // If aligned, relative position p_i = 0.
    
    // For each ring i from 1 to n-1
    for (int i = 1; i < n; ++i) {
        // Coarse search for peaks
        // We look for rotation r such that unblocked count is high.
        // We use stride m.
        int best_val = -1;
        vector<int> candidates; 
        
        // We need a baseline. Let's get current value.
        // Rotate ring i by 0 (dummy)? No, just rotate by 1 and -1 if needed?
        // Or just start scanning.
        
        // We will rotate ring i by m repeatedly.
        // There are N/m steps.
        int steps = N / m;
        
        // Store (rotation_from_current, value)
        // We track cumulative rotation.
        int current_rot = 0;
        
        // Initial value check?
        // Let's do a small wiggle to get initial value without moving much
        int val = query(i, 1);
        val = query(i, -1); // rotate back
        
        // Actually, just start the loop.
        // We need to cover full circle.
        // We can just query after each block of m rotations.
        // But we want to find the BEST rotation.
        
        // Optimization: Use a smaller stride? Or random?
        // Stride m is good for detection.
        // We'll record potential peaks.
        
        int global_max = -1;
        vector<int> peak_rots;
        
        for (int s = 0; s < steps; ++s) {
            int res = rotate_ring(i, m);
            current_rot += m;
            if (res > global_max) {
                global_max = res;
                peak_rots.clear();
                peak_rots.push_back(current_rot);
            } else if (res == global_max) {
                peak_rots.push_back(current_rot);
            }
        }
        
        // Now we have candidate coarse rotations.
        // We need to refine them (local search) and distinguish ring 0 alignment.
        // The ring i is currently at offset +N (full circle) effectively 0 relative to start of loop.
        // current_rot is N.
        
        // Let's bring ring i back to 0 effectively to simplify logic, 
        // or just work with modulo arithmetic.
        // Actually, we rotated N times, so we are back at start.
        // current_offset[i] is back to original (mod N).
        
        // For each candidate coarse peak, we search locally [peak-m, peak+m]
        // to find the true local maximum.
        
        int true_best_val = -1;
        vector<int> best_candidates;
        
        for (int coarse : peak_rots) {
            // Normalize coarse to usually be around 0..N-1
            // We want to go to coarse - m.
            // Calculate delta from current (0).
            int target = coarse - m; 
            // We might have multiple candidates. The current pos is 0 (relative to start of loop).
            // We just move to target.
            
            // Wait, we need to minimize movement.
            // But n is small, 100 loops of this is fine.
            
            // Move to coarse - m
            // Since we are at 0, rotate by (coarse - m).
            // Note: coarse is multiple of m.
            int move = (target % N + N) % N;
            if (move > N/2) move -= N;
            
            rotate_ring(i, move); 
            int local_offset = move; // relative to start of loop
            
            // Scan locally 2m steps
            for (int k = 0; k < 2 * m; ++k) {
                int res = rotate_ring(i, 1);
                local_offset++;
                
                if (res > true_best_val) {
                    true_best_val = res;
                    best_candidates.clear();
                    best_candidates.push_back(local_offset);
                } else if (res == true_best_val) {
                    best_candidates.push_back(local_offset);
                }
            }
            
            // Return to 0
            rotate_ring(i, -local_offset);
        }
        
        // Now we have precise rotation amounts (relative to start of loop) that give max unblocked.
        // We need to find which one corresponds to ring 0.
        // Test: Move ring 0 by 1. Check if the peak value changes (or drops).
        // If ring i is aligned with ring 0, moving ring 0 should degrade the alignment (value drops),
        // UNLESS ring 0 moves in sync with ring i (which we don't do).
        // Wait, if we move ring 0, the 'sweet spot' moves.
        // If ring i is at the sweet spot (aligned with 0), and we move ring 0 away, unblocked decreases.
        // If ring i is aligned with ring j (j!=0), and we move ring 0 away, unblocked might stay same 
        // (if ring 0 was not interacting) or change differently.
        // Actually, simplest check:
        // Move ring i to candidate. 
        // Move ring 0 by 1.
        // If ring i follows ring 0, the value should be maintained? No we don't move i.
        // If aligned, ring 0 and i are on top of each other.
        // Moving ring 0 by 1 separates them. Union size increases. Unblocked DECREASES.
        // If ring i is on top of ring j, moving ring 0 (which is elsewhere) shouldn't affect the stack at j significantly.
        // (Unless ring 0 was also there, but then we have a triple stack).
        
        int chosen_rot = -1;
        
        // Sort and unique candidates
        sort(best_candidates.begin(), best_candidates.end());
        best_candidates.erase(unique(best_candidates.begin(), best_candidates.end()), best_candidates.end());

        for (int cand : best_candidates) {
            // Move to cand
            int move = (cand % N + N) % N;
            if (move > N/2) move -= N;
            rotate_ring(i, move);
            
            // Check sensitivity to ring 0
            int v1 = query(0, 0); // dummy? No, query returns value.
            // Just assume current value is v1 (we tracked it? No, query needed).
            // We can do ? 0 1 then ? 0 -1.
            v1 = rotate_ring(0, 1);
            int v2 = rotate_ring(0, -1);
            
            // If aligned, separating them reduces unblocked.
            // v2 is value at alignment. v1 is value when separated by 1.
            // Expect v1 < v2.
            // If not aligned (ring 0 far away), v1 approx v2.
            // (Ring 0 moving in empty space or constant noise).
            
            if (v1 < v2) {
                // Found it!
                chosen_rot = cand;
                // Stay here? No, we rotate back to 0 to be clean, then apply chosen at end?
                // Or just break and we are at correct spot.
                // We are currently at 'cand'.
                // We verified it.
                // But wait, we moved ring 0 back.
                // So we are in state: ring i at cand, ring 0 at original.
                // This is the aligned state.
                // We can stop search for this ring.
                break;
            }
            
            // Move back to 0
            rotate_ring(i, -move);
        }
        
        if (chosen_rot == -1) {
            // Fallback: pick the first one?
            // Should not happen if logic is correct and gap exists/stacking works.
            // If multiple stacks exist, picking any might be valid if they are equivalent.
            // But we need to report positions at the END.
            // If we leave ring i aligned with ring j, we must report its position relative to ring 0.
            // But we want to align with ring 0 so we can report 0.
            // If verification failed, maybe ring 0 is somehow stuck?
            // Just take the first candidate and hope.
             if (!best_candidates.empty()) {
                int move = (best_candidates[0] % N + N) % N;
                if (move > N/2) move -= N;
                rotate_ring(i, move);
             }
        }
        // Ring i is now aligned with ring 0.
    }
    
    // Output result
    // Since all rings are aligned with ring 0, relative positions are 0.
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " " << 0;
    }
    cout << endl;
    
    return 0;
}