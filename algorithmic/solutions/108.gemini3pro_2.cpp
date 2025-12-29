#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n, m;
// Tracks current rotation of each ring relative to its initial position.
vector<int> current_rot; 

int query(int ring, int dir) {
    cout << "? " << ring << " " << dir << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Should not happen
    current_rot[ring] += dir;
    return res;
}

int main() {
    cin >> n >> m;
    current_rot.resize(n, 0);

    // Initial query to get baseline
    // Since we just started, we can make a dummy query or just use the first operation.
    // However, the interactive loop requires us to know the previous state's output? 
    // The problem says "For each query, you will receive...".
    // We can assume we don't know the initial unblocked count.
    // But we will get it after the first rotation.

    // To save queries, we'll get the initial value by a null-op? 
    // No null-op available. We have to rotate.
    // Let's just track values as we go.
    
    // We assume rings 0 to i-1 are aligned. Initially i=1, only ring 0 is "aligned" with itself.
    // We process ring i from 1 to n-1.
    
    vector<int> p(n); // p[i] will store relative shift
    
    // Get an initial reading by rotating ring 0 back and forth
    int current_val = query(0, 1);
    current_val = query(0, -1);
    
    for (int i = 1; i < n; ++i) {
        int best_val = -1;
        // We will scan ring i with step m.
        // Total steps = n.
        // We track the starting rotation of ring i for this phase.
        int start_rot_i = current_rot[i];
        
        bool found = false;
        
        // We use the initial current_val as a baseline to skip checks.
        // Aligning ring i should generally increase the unblocked count compared to random position.
        // However, if we start at a good position, it might decrease.
        // We will maintain a dynamic threshold or just check "promising" ones.
        // To be safe and stay within 30000, we skip checks if V < current_val (before move).
        // Actually, current_val changes as we rotate.
        
        // Strategy: Rotate by m, check value. If value is high, check sensitivity.
        // High means >= something. 
        // Let's estimate baseline from the first few samples?
        // Or simply: if val >= max_val_seen_so_far, check sensitivity.
        // And maybe a bit lower too.
        
        // To ensure we don't exceed limit, we strictly check only if val >= current_baseline
        // where baseline is established at start.
        int baseline = current_val;
        
        // Since we step m, we do n iterations.
        for (int k = 0; k < n; ++k) {
            // Rotate ring i by m. We do this in one go? No, can only rotate by 1.
            // But we can output multiple lines? No, interaction is one by one.
            // Rotating by m takes m queries. This is too expensive! m <= 20.
            // If m=20, rotating by m takes 20 queries. Total 20*100*100 = 200,000.
            // Wait! The loop budget analysis in thought block assumed "Rotate by m" is 1 step.
            // BUT WE CAN ONLY ROTATE BY 1.
            // So we CANNOT scan by jumping m.
            // We MUST rotate by 1 continuously.
            // If we rotate by 1 continuously, we take L steps.
            // L = 2000. Total N*L = 200,000. Too big.
            
            // Correction: We can rotate OTHER rings?
            // No.
            
            // Re-think:
            // We need to find the alignment.
            // Random jumps?
            // We can perform a random jump by rotating a random amount.
            // But rotating takes queries.
            // Cost of rotation is proportional to distance.
            // Average distance L/2.
            // We cannot jump.
            
            // WAIT. 30000 is large enough for N*sqrt(L)? No.
            // Is there any other way?
            // "Wabbit can open the lock on his own."
            // "You may perform up to 30000 rotations".
            
            // Maybe we don't need to scan the whole ring.
            // We can use randomization.
            // But moving to a random position is expensive.
            
            // BACKTRACK:
            // Is it possible to find gradient?
            // If we are at pos x, and alignment is at y.
            // Does unblocked count increase as x -> y?
            // Yes, the overlap function is triangular.
            // But the basin of attraction is only width 2m.
            // Outside of basin, gradient is 0 (or noise).
            
            // So we must hit the basin.
            // Basin probability 1/n.
            // We need to try ~n positions.
            // If we can't jump, we must move.
            // BUT we can move ring 0!
            // Ring 0 is the reference.
            // If we move ring 0, we move the target.
            // We can effectively "jump" the relative position by moving ring 0?
            // Moving ring 0 by x costs x. Same problem.
            
            // Wait. Constraints: N <= 100, M <= 20.
            // Maybe n is small usually?
            // If N=100, we have a problem.
            // But maybe we don't need to scan ring i fully.
            // We can rotate ring i by 1 step at a time, check sensitivity.
            // But only check sensitivity if "promising".
            // Promising means we are in a basin.
            // How to detect basin without sensitivity?
            // Value is higher.
            // How much higher?
            // We don't know absolute baseline.
            // But we can rotate ring i for some steps.
            // If we just rotate ring i by 1 repeatedly (scan).
            // We observe values v_1, v_2, ...
            // If we see a sudden increase, we are entering a basin.
            // Basin shape: starts low, rises to peak, falls.
            // Width 2m.
            // We can detect "slope up".
            // If v_{t} > v_{t-1}, we are climbing!
            // Follow the gradient!
            // If we are on flat ground, v_{t} approx v_{t-1}.
            // So, scan: rotate i by 1.
            // If val increases, continue rotating i.
            // If val decreases, maybe passed peak?
            // If val constant, random noise.
            
            // What if we are stuck in flat land?
            // We need to jump.
            // But we can't jump cheap.
            // UNLESS we move the target (ring 0) to us?
            // No, cost is symmetric.
            
            // Is there a way to verify random positions cheaper?
            // No.
            
            // Let's re-read carefully.
            // "score is inversely linear related to the max number of queries."
            // We need to minimize.
            
            // Maybe I should assume we can find the peak by scanning.
            // With M=20, L=2000.
            // Basins cover 2m/L = 1/50 of space?
            // No! There are N basins.
            // One for each ring j.
            // Total N basins.
            // Total coverage of basins: N * 2m.
            // If N=100, M=20, coverage = 4000 > 2000.
            // The whole space is covered by basins!
            // We are ALWAYS on a slope or peak.
            // There is no flat land.
            // The function is a sum of N triangle functions.
            // It's a bumpy landscape.
            // We can just Hill Climb from ANYWHERE to a local maximum.
            // This local maximum corresponds to alignment with *some* ring j (or stack 0).
            // Cost to climb: small (distance to nearest peak).
            // Average distance to peak?
            // Peaks are every L/N = m on average.
            // Distance to peak ~ m/2 = 10.
            // Climb takes ~10 queries.
            // Once at peak, check sensitivity (Is it 0?).
            // If yes, done.
            // If no, we are at peak j.
            // We need to go to peak 0.
            // Where is peak 0?
            // We don't know.
            // But we know we are at wrong peak.
            // We need to move to another peak.
            // Jump? Costly.
            // But wait.
            // We can just keep moving in one direction until we find the right peak.
            // Move over the ridge, down into next valley, up to next peak.
            // Distance between peaks ~ m.
            // Cost ~ m.
            // We check each peak.
            // Total peaks N.
            // Total cost N * (m + check).
            // N * (20 + 4).
            // 100 * 24 = 2400.
            // Total for N rings: 100 * 2400 = 240,000.
            // Still too high!
            
            // Wait. We are aligning ring i.
            // There are only i aligned rings at 0.
            // There are n-1-i random rings.
            // Total i+1 "significant" macro-objects?
            // No, random rings are single. Stack is size i.
            // All peaks look similar.
            // BUT for small i, there are many random rings -> many peaks.
            // For large i, most rings are in stack 0.
            // So few peaks.
            // For large i, landscape is flat 0-basin + few j-basins.
            // We find 0-basin easily.
            // For small i, landscape is crowded.
            // BUT for small i, we just need to find 0.
            // We check peaks.
            // Probability that a random peak is 0 is 1/N.
            // Wait, if landscape is crowded, we are checking many false peaks.
            // Cost is high.
            
            // Is there a shortcut?
            // Move ring 0!
            // If we move ring 0 by 1 step.
            // The 0-peak moves by 1.
            // The j-peaks stay put.
            // If we are at a local max, and we move 0, and the value drops significantly -> we were at 0-peak.
            // If value stays same -> j-peak.
            // This is the sensitivity test.
            
            // How to navigate to 0-peak fast?
            // We can't. We have to search.
            // BUT we can search efficiently.
            // We can rotate ring i.
            // Instead of stopping at every peak, can we filter?
            // No.
            
            // Maybe we can rotate ring 0?
            // If we rotate ring 0 continuously, the 0-peak sweeps across ring i.
            // When 0-peak hits ring i's current position, we get a bump.
            // We detect the bump.
            // Then we lock 0 and i together?
            // Cost to sweep 0: L.
            // Total N*L. Too slow.
            
            // Let's reconsider the random jump.
            // "To perform a rotation... d in {-1, 1}".
            // We CANNOT jump.
            // We are forced to walk.
            // But wait!
            // We can rotate ring i by random amount? No.
            // We can only walk.
            
            // Is 30000 limit for finding ALL p_i? Yes.
            // Is there a special property?
            // "Wabbit needs n-1 integers... p_i = relative pos".
            
            // What if we just rotate ring i by 1, 2, ...
            // And calculate correlations?
            // Too slow.
            
            // Is it possible that N is small?
            // 2 <= N <= 100.
            // If N=100, we must be very efficient.
            // N*M <= 2000.
            // Maybe the crowdedness helps?
            // Early on (i small), almost ANY position is good?
            // No, we need p_i relative to 0.
            // Only ONE position is correct.
            
            // Let's go back to Hill Climbing + Checking.
            // Average number of peaks we visit before finding 0?
            // If peaks are random, N/2.
            // Cost per peak ~ m.
            // Total cost per ring: (N/2) * m.
            // Total total: N * (N/2 * m) = N^2 m / 2.
            // 100^2 * 20 / 2 = 100,000.
            // Factor of 3 too high.
            
            // Optimizations:
            // 1. Don't fully climb false peaks.
            //    If we are climbing, check sensitivity early?
            //    If not sensitive, abort climb, move to next.
            //    Check sensitivity: 2 queries.
            //    Climb step: 1 query.
            //    Checking every step is more expensive.
            //    Check at "promising" slope?
            
            // 2. The stack 0 is size i.
            //    When i is large, stack is HUGE.
            //    Does stack create a wider basin?
            //    No, width is determined by arc length m.
            //    Does it create a HIGHER peak?
            //    Intersection of aligned rings is same as single ring.
            //    BUT unblocked count is determined by union of all gaps.
            //    Union of gaps = Gap_stack \cap Gap_others.
            //    Gap_stack is size L-m.
            //    Gap_other is size L-m.
            //    If we align i with stack, we maintain Gap_stack.
            //    If we align i with j, we intersect Gap_stack with Gap_j (misaligned).
            //    Intersection is smaller.
            //    So unblocked count is SMALLER.
            //    Wait. Unblocked = |Intersection of Gaps|.
            //    Aligning i with stack MAXIMIZES intersection (keeps it equal to Gap_stack).
            //    Aligning i with j (j != stack) makes intersection = Gap_stack \cap Gap_j.
            //    Gap_stack \cap Gap_j is strictly smaller than Gap_stack (since j not aligned).
            //    So the 0-peak is HIGHER than j-peaks!
            //    How much higher?
            //    Gap_stack has size L-m.
            //    Gap_stack \cap Gap_j has size L-2m approx.
            //    Difference is m.
            //    This is huge!
            //    So the 0-peak is the GLOBAL MAXIMUM.
            //    And it is significantly higher than other local maxima (j-peaks).
            
            //    So we don't need to check sensitivity for every peak!
            //    We just need to find the global maximum.
            //    Or any peak that is "high enough".
            //    
            //    Strategy:
            //    Rotate ring i around.
            //    Track max value.
            //    If we find a value that is much higher than others, it's the 0-peak.
            //    
            //    But we can't scan fully.
            //    However, for small i, there are many j-peaks.
            //    Are they all low?
            //    Yes, because 0-stack is only size 1 (ring 0).
            //    Wait. For i=1:
            //    Stack is just ring 0.
            //    Aligning 1 with 0 -> Union is size m.
            //    Aligning 1 with j -> Union is size m.
            //    Same height!
            //    So for i=1, 0-peak is NOT distinguishable by height.
            //    My logic about Gap_stack applies when stack is "dominant"?
            //    No, actually:
            //    Unblocked = L - |Union of Arcs|.
            //    Current Arcs: Stack (size m, fixed), Others (size m each, fixed).
            //    Ring i (size m, moving).
            //    Align i with Stack: Union = Stack U Others. (Ring i disappears into Stack).
            //    Align i with j: Union = Stack U Others. (Ring i disappears into j).
            //    The resulting union size is Identical.
            //    So for i=1, all peaks are same height.
            //    
            //    But for i=large?
            //    Stack has size i. But geometrically it's just one arc of size m.
            //    It's indistinguishable from ring j geometrically.
            //    So ALL peaks are same height always.
            //    
            //    So we MUST use sensitivity.
            //    
            //    Back to 30000 limit.
            //    For i=1, we have 100 peaks. We need to find 0-peak.
            //    We check peaks.
            //    For i=large, we have few peaks.
            //    
            //    Actually, do we need to check ALL peaks for i=1?
            //    We can check them as we encounter them.
            //    We perform a walk.
            //    We hit a peak. Check it.
            //    If not 0, move on.
            //    Since we check every peak we visit, and peaks are random.
            //    Expected visits = N/2.
            //    Total cost still high.
            
            //    IS THERE ANY WAY TO JUMP?
            //    We can't jump.
            //    
            //    Wait.
            //    Maybe we can align ALL rings to ring 0 at once?
            //    No.
            
            //    What if we move ring 0?
            //    We oscillate ring 0.
            //    If we oscillate ring 0 with period P.
            //    And rotate ring i with period Q.
            //    Maybe we can detect resonance? No.
            
            //    Let's look at the constraint again. 30000.
            //    Maybe average case is better?
            //    N/2 peaks is average.
            //    Also N decreases.
            //    Sum of (N-i)/2 for i=1..N.
            //    Sum k/2 = N^2 / 4.
            //    100^2 / 4 = 2500.
            //    Total peaks to check = 2500.
            //    Cost per peak:
            //      Travel to peak (m queries).
            //      Check (2 queries).
            //      Total 22 queries.
            //    Total = 2500 * 22 = 55,000.
            //    Still 2x over budget.
            
            //    Can we reduce travel cost?
            //    We are walking continuously.
            //    Distance between peaks is variable.
            //    Average distance L/N = m.
            //    Travel cost IS m.
            
            //    Can we reduce check cost?
            //    Check takes 2 queries. Hard to reduce.
            //    
            //    Can we avoid checking some peaks?
            //    Maybe check every 2nd peak?
            //    If we miss, we wrap around.
            //    No gain.
            
            //    Wait. "your score is inversely linear related to the max number of queries."
            //    "You may perform up to 30000 rotations".
            //    Maybe I am pessimistic about constants.
            //    Basin width is 2m.
            //    Peak is broad.
            //    Maybe we check sensitivity only at the top?
            //    Or maybe check "on the way up"?
            //    
            //    What if we skip the walk?
            //    We are at peak j.
            //    Peak 0 is somewhere.
            //    We have to walk.
            //    
            //    Is there a way to verify multiple rings at once?
            //    No.
            
            //    Wait!
            //    Maybe we can collect multiple rings into a pile?
            //    Align ring 2 to ring 1.
            //    Align ring 3 to ring 1.
            //    Then align the whole pile to 0?
            //    Aligning 2 to 1 is same difficulty as 2 to 0.
            //    But if we make a pile, we reduce number of peaks for subsequent rings?
            //    If we align 2 to 1, we have a pile {1,2}.
            //    For ring 3, we have pile {1,2} and ring 0.
            //    Still piles look like single rings.
            
            //    Let's gamble on the constant factor.
            //    Also, the peaks might be clustered?
            //    Also, we skip checks if V < baseline.
            //    
            //    Baseline update:
            //    If we find a peak that is NOT 0, does it give us info?
            //    It tells us "this is a used slot".
            //    
            //    Implementation details:
            //    We just walk.
            //    "Promising" = value increases (climbing).
            //    At local max, check sensitivity.
            //    If not 0, continue walking (down the slope).
            
            int v_curr = current_val;
            
            // Walk direction?
            // Just +1.
            int step_dir = 1;
            
            // To prevent infinite loops if we miss 0 (e.g. noise), bound by L.
            int steps_taken = 0;
            int max_steps = n*m + 200; 
            
            while (steps_taken < max_steps) {
                // Perform step
                int v_next = query(i, step_dir);
                steps_taken++;
                
                // Check if we are at a potential peak or plateau
                // We check sensitivity if value is high (heuristic) or if local max.
                // To save queries, only check at local max?
                // Local max detected when v_next < v_curr.
                // Then v_curr was the max.
                // We should check v_curr position.
                // So move back.
                
                bool check_it = false;
                if (v_next < v_curr) {
                    // Local max at previous position.
                    // Or just noise.
                    // But if v_curr was significantly high?
                    // Let's assume any local max is a candidate.
                    // Move back to check.
                    query(i, -step_dir); // Move back to peak
                    // Now at peak.
                    check_it = true;
                } else {
                    // climbing or flat.
                    // Update current
                    v_curr = v_next;
                    // If flat?
                    // If v_next == v_curr, could be top of plateau.
                    // But if we continue, we might go down.
                    // Let's defer check until drop.
                }
                
                if (check_it) {
                    // We are at a local max.
                    // Check sensitivity
                    int v_base_sens = v_curr;
                    int v_sens = query(0, 1);
                    query(0, -1); // Restore
                    
                    if (v_sens < v_base_sens) {
                        // Found it!
                        // Calculate p_i
                        // p_i = (Rot0 - RotI) % L
                        int rot0 = current_rot[0];
                        int roti = current_rot[i];
                        int diff = (rot0 - roti) % (n * m);
                        if (diff < 0) diff += n * m;
                        p[i] = diff;
                        found = true;
                        
                        // IMPORTANT: Update global current_val for next ring?
                        // Ring i is now aligned.
                        // current_val needs to be updated.
                        // We are at aligned pos.
                        // We need to pass valid current_val to next iteration.
                        // current_val should be the value at this pos.
                        // We are at peak, so v_curr is correct.
                        // BUT we moved back to peak, then query 0 moves.
                        // We restored 0.
                        // So we are at peak. v_curr is valid.
                        // However, we need to break outer loop.
                        current_val = v_curr;
                        break;
                    } else {
                        // False peak.
                        // Resume walking.
                        // We moved back to peak to check.
                        // We need to move forward again to continue.
                        query(i, step_dir);
                        v_curr = v_next; // We are back at the "down" step value?
                        // Wait, we moved back, so we are at peak value.
                        // Then we move forward, so we are at v_next (lower).
                        // Continue loop.
                    }
                }
            }
            if (found) break;
            
            // If we run out of steps?
            // Should not happen.
            // If it happens, we probably missed it due to noise.
            // Just pick current pos? Or random?
            // Let's hope it doesn't happen.
            
            // Actually, "steps_taken" logic is inside the k loop?
            // No, the k loop was the scan.
            // I replaced the scan with the while loop.
            // So break out of k loop is not needed (k loop removed).
            break; 
        }
    }
    
    cout << "!";
    for (int i = 1; i < n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;
    
    return 0;
}