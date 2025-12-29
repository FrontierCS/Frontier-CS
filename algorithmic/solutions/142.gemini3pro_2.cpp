#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Structure to represent a move
struct Move {
    int from;
    int to;
};

int n, m;
// stacks[i] stores the colors of balls in pole i+1 (0-indexed internally, but output 1-indexed)
// Top of stack is back of vector
vector<vector<int>> poles;
vector<Move> operations;

// Helper function to perform a move
void perform_move(int from, int to) {
    operations.push_back({from + 1, to + 1});
    int ball = poles[from].back();
    poles[from].pop_back();
    poles[to].push_back(ball);
}

// Function to move count balls from 'from' to 'to'
void move_k(int from, int to, int count) {
    for (int i = 0; i < count; ++i) {
        perform_move(from, to);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    poles.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }
    // Pole n (index n) is initially empty

    // Iterate through each color to consolidate
    for (int target_color = 1; target_color <= n; ++target_color) {
        // We will collect all balls of target_color into pole (target_color - 1)
        int target_pole = target_color - 1;
        
        // Step 1: Separate existing target balls in target_pole from others
        // Move all to buffer (pole n), then filter back
        // Optimization: If pole is already sorted or pure, skip/simplify
        // But for safety, full separation.
        
        // Move all balls from target_pole to buffer
        int initial_size = poles[target_pole].size();
        move_k(target_pole, n, initial_size);
        
        // Now move back: target_color balls first (to be at bottom), others later
        // But we can only pop from top of buffer.
        // Buffer has balls in reverse order of original target_pole.
        // We want target_color at bottom of target_pole.
        // Strategy:
        // 1. Move everything from buffer to target_pole. Count target balls.
        //    While moving, if we see target, we want it at bottom.
        //    This is circular.
        
        // Correct Filter with 1 empty pole (target_pole is now empty, buffer is full):
        // We have: Buffer (full), Target_Pole (empty).
        // Iterate balls in Buffer (top to bottom).
        // If ball is target_color -> Move to Target_Pole.
        // If ball is NOT target_color -> We want to put it in Target_Pole ON TOP of target_color balls.
        // Wait, we want target_color at BOTTOM.
        // So we want to push target_color balls into Target_Pole FIRST.
        // But we access Buffer from top.
        // If top is target, move to Target_Pole. Good.
        // If top is NOT target, we must put it somewhere.
        // Put in Target_Pole? It will be covered by subsequent target balls. Bad.
        // Put in... wait, we have n+1 poles.
        // Poles 0..n-1 are full/mixed. Pole n is Buffer.
        // Currently target_pole is empty. Pole n is full (of stuff from target_pole).
        // We can use any OTHER pole j to temporarily hold non-target balls?
        // Other poles are full (size m). Can't push.
        // BUT, for the logic of the problem, we process colors 1..N.
        // When processing color k, poles 0..k-1 are DONE (full of correct color).
        // Poles k+1..n-1 are mixed.
        // Pole k (target_pole) is the one we are fixing.
        
        // So we can use poles k+1..n-1 as temporary storage? No, they are full.
        // Only target_pole and Buffer (pole n) have space.
        
        // Let's go back to: We dumped target_pole to Buffer.
        // Now target_pole is empty.
        // We want to extract target balls from Buffer and put in target_pole.
        // Non-target balls should also go to target_pole (on top) or stay in Buffer?
        // We want target_pole to be: [Target...Target, Junk...Junk].
        // So we need to put Target balls first.
        
        // If we encounter non-target in Buffer, we can't put it in target_pole yet.
        // We must keep it in Buffer? But we need to access below it.
        // We can rotate Buffer!
        // Move non-target from Buffer to Target_Pole.
        // Later, we will move them back to Buffer to uncover targets?
        // This effectively reverses the non-targets?
        
        // Let's count how many target balls we have in Buffer.
        int t_count = 0;
        for (int x : poles[n]) if (x == target_color) t_count++;
        int other_count = poles[n].size() - t_count;
        
        // Naive sort:
        // While we haven't extracted all t_count targets:
        //   Pick top of Buffer.
        //   If target: move to Target_Pole (stays there).
        //   If other: move to Target_Pole (temporary).
        // After emptying Buffer, Target_Pole has mixed.
        // But targets are relatively distributed.
        // We want all targets at bottom.
        // This looks like bubble sort. Too slow?
        
        // Better:
        // Since we are building Target_Pole for the first time, maybe we don't care about order yet?
        // We just need to separate Junk to Buffer eventually.
        // Let's just put all Target balls from Buffer to Target_Pole, and all Junk to Buffer?
        // We can't do that directly.
        // But we can collect Good balls.
        
        // Use the sifting algorithm from thought process:
        // Current state: Buffer full (source), Target_Pole empty (dest).
        // We want Target_Pole to have [Target...Target].
        // Buffer will end up with [Junk...Junk].
        
        // Loop:
        // 1. Move all non-targets from Buffer to Target_Pole. Keep targets in Buffer?
        //    Can't peek deep.
        
        // Let's use the 'Fetch' logic for the initial balls too.
        // Dump Buffer back to Target_Pole.
        // Now Target_Pole is full. Buffer empty.
        // Sort Target_Pole:
        //   Move all to Buffer.
        //   Move back to Target_Pole:
        //     If target -> Keep in Buffer? No.
        //     If target -> Move to Target_Pole.
        //     If other -> Move to Target_Pole.
        //   This doesn't change anything.
        
        // Actually, we can move non-targets to OTHER poles?
        // We have free space of size M distributed between Target_Pole and Buffer.
        // Iterate j > target_pole.
        // Swap non-targets from Target_Pole with targets from j?
        // That's the main loop.
        // So, initially, just treat ALL balls in Target_Pole as "Junk" unless they are already at bottom?
        // No, simplest is: Treat Target_Pole as mixed.
        // We want to end up with Target_Pole full of target_color.
        // Current Target_Pole has some target balls.
        // Move all non-target balls from Target_Pole to Buffer.
        // BUT we need to keep target balls at bottom.
        // This requires sorting Target_Pole.
        
        // Sorting single stack P using empty E:
        // 1. Move all P -> E.
        // 2. Scan E (top to bottom).
        //    If top is Good: Move E -> P.
        //    If top is Bad: Move E -> P.
        //    This preserves order (reverse of reverse = original).
        // To change order:
        //    We need to hold Bad balls while passing Good balls.
        //    Where? We only have P and E.
        //    Hold Bad in P? Good in P?
        //    If we put Bad in P, they block Good.
        //    If we put Good in P, they are blocked by Bad later?
        //    We want Good at bottom.
        //    So we must put Good in P first.
        //    When we see Bad in E, we must NOT put it in P yet.
        //    But we must remove it from E to see next.
        //    Where to put?
        //    We can put in P!
        //    But then P has [Bad]. Next we see Good. Move E->P.
        //    P has [Bad, Good]. Wrong order.
        
        // However, we can fix [Bad, Good] -> [Good, Bad] using E.
        // P -> E (Good). P -> E (Bad).
        // E -> P (Bad). E -> P (Good).
        // Ops: 4.
        // Bubble sort!
        // Cost O(M^2). M=400 -> 160,000. Acceptable.
        
        // Sort Target_Pole (Bubble Sort):
        // P is Target_Pole. E is n.
        // We want target_color at bottom.
        // We can count targets. Let K be count.
        // We want bottom K to be target.
        // Bubble up non-targets? Or bubble down targets?
        // Bubble down targets.
        // For i from 0 to K-1:
        //   Find i-th target ball from bottom.
        //   Bring to position i.
        
        // Better: Selection Sort logic.
        // Find deep target. Bring to top. Then move to E (hold).
        // Repeat K times.
        // Then move K targets E -> P.
        // Then move remaining (Junk) E -> P.
        // Actually, Junk is already in P or E?
        // Let's refine:
        // 1. Move all P -> E.
        // 2. Loop:
        //    Find first Target in E (from top).
        //    Let depth be d.
        //    Move d Bad balls E -> P.
        //    Move Target E -> P.
        //    Move d Bad balls P -> E.
        //    Now P has 1 Target at top? No, we moved it to P.
        //    Wait, we want Targets at BOTTOM of P.
        //    So we should collect Targets in P.
        //    But we put Bad balls in P temporarily to dig.
        //    We moved them back to E.
        //    So P has 1 Target. E has all Bad + remaining Targets.
        //    Repeat.
        //    Next Target in E... Same logic.
        //    P accumulates Targets.
        //    Finally P has all Targets. E has all Bad.
        //    Move all Bad E -> P.
        //    P is sorted: [Targets... Bad...].
        //    Cost: Sum(2*depth) approx M^2.
        
        move_k(target_pole, n, poles[target_pole].size()); // P -> E
        
        int collected = 0;
        int total_targets = 0;
        for(int x : poles[n]) if(x == target_color) total_targets++;
        
        for(int k=0; k<total_targets; ++k) {
            // Find next target in E (from top)
            int d = 0;
            // E is accessed from back.
            // poles[n].rbegin() is top.
            // We need index.
            int idx = -1;
            for(int i = poles[n].size() - 1; i >= 0; --i) {
                if(poles[n][i] == target_color) {
                    idx = i;
                    break;
                }
            }
            // depth d is distance from top
            d = poles[n].size() - 1 - idx;
            
            // Move d balls E -> target_pole
            move_k(n, target_pole, d);
            
            // Move target E -> target_pole
            move_k(n, target_pole, 1);
            
            // Move d balls target_pole -> E
            // But wait! We moved target to target_pole. It is at top.
            // We want to KEEP target in target_pole.
            // The d balls are BAD balls (or future targets).
            // We want to return them to E.
            // But target is ON TOP of them in target_pole?
            // No, we moved d balls, then 1 target.
            // target_pole top: Target. Below: d balls.
            // We can't pop the d balls without popping Target.
            
            // Fix: Move Target back to E? No.
            // We want Target at BOTTOM of target_pole.
            // Currently target_pole has [Collected Targets] at bottom.
            // Then [d balls]. Then [Target].
            // We want [Collected] [Target] [d balls].
            // We need to swap [d balls] and [Target].
            
            // Helper: "Rotate" top d+1 balls in target_pole?
            // Top is Target. Next d are Bad.
            // We can move Target -> E.
            // Move d Bad -> E.
            // Move Target -> target_pole.
            // Move d Bad -> target_pole? No we want Bad in E.
            // So:
            // 1. Move d balls E -> target_pole.
            // 2. Move Target E -> target_pole.
            // State: P has [Collected] [d Bad] [Target].
            // 3. Move Target P -> E.
            // 4. Move d Bad P -> E.
            // 5. Move Target E -> P.
            // State: P has [Collected] [Target]. E has [Rest] [d Bad].
            // The d Bad are now on top of E. Order changed but set is same.
            
            // Optimization: The d balls we moved out were from E top.
            // We put them back to E top.
            
            move_k(target_pole, n, 1); // Target back to E
            move_k(target_pole, n, d); // Bad back to E
            move_k(n, target_pole, 1); // Target to P
        }
        
        // After loop, P has [All Targets]. E has [All Junk].
        // Move Junk back to P?
        // No! We want Junk in E to separate them.
        // But we need to make space in E if it's too full?
        // Actually, we want P to be [Targets... Empty...].
        // E has [Junk...].
        // P space = M - total_targets.
        // E space = total_targets.
        // Total space = M.
        
        // Now P contains only targets. E contains only Junk.
        // Start fetching more targets from other poles.
        
        int p_count = total_targets; // Number of targets in P
        
        // Loop until P is full
        while(p_count < m) {
            // Find best target ball in j > target_pole
            int best_j = -1;
            int min_depth = 1e9;
            
            for(int j = target_pole + 1; j < n; ++j) {
                // Find depth of first target_color
                int depth = -1;
                for(int i = poles[j].size() - 1; i >= 0; --i) {
                    if(poles[j][i] == target_color) {
                        depth = poles[j].size() - 1 - i;
                        break;
                    }
                }
                if(depth != -1) {
                    if(depth < min_depth) {
                        min_depth = depth;
                        best_j = j;
                    }
                }
            }
            
            // We are guaranteed to find one because total count is m per color
            int j = best_j;
            int d = min_depth;
            
            // Fetch logic
            // We need to move d balls from j.
            // P space: m - p_count.
            // E space: p_count (since E has m - p_count Junk).
            // Actually check current E size:
            // poles[n].size() is the number of Junk balls.
            // Size is m - p_count.
            // Space in E is m - (m - p_count) = p_count.
            // Can we fit d balls?
            // We can split d balls between P and E.
            
            int move_to_E = min(d, p_count);
            int move_to_P = d - move_to_E;
            
            // 1. Move to E
            move_k(j, n, move_to_E);
            
            // 2. Move to P
            move_k(j, target_pole, move_to_P);
            
            // 3. Move Target to P
            move_k(j, target_pole, 1);
            p_count++;
            
            // 4. Restore: Move balls back to j
            // Order: We moved move_to_P balls to P (sitting below Target? No, P is stack)
            // P state: [Targets_Old] [Bad_Part2] [Target_New].
            // We want Target_New to be on top of Targets_Old.
            // We need to remove Bad_Part2.
            // Also need to return Bad_Part1 from E.
            
            // Current P top is Target_New.
            // Below it is Bad_Part2 (size move_to_P).
            
            // Move Target_New to E?
            // E has Bad_Part1 on top.
            // If we move Target_New to E, it buries Bad_Part1.
            // Then we can move Bad_Part2 P->j.
            // Then move Bad_Part1 E->j? No, Target_New blocks.
            
            // We need Target_New to stay in P (or go to safe place).
            // Safe place is P (bottom).
            // Swap Target_New with Bad_Part2?
            // P: [Old] [Bad2] [New].
            // Op:
            // Move New -> E. (E: [Junk] [Bad1] [New])
            // Move Bad2 -> j. (Restored part 2)
            // Move New -> P. (P: [Old] [New])
            // Move Bad1 -> j. (Restored part 1)
            
            // This works IF E has space for New.
            // E usage: (m - (p_count-1)) [Junk] + move_to_E [Bad1].
            // Note p_count increased by 1.
            // Original Junk count was m - (p_count - 1).
            // E size = m - p_count + 1 + move_to_E.
            // Capacity m.
            // Space = p_count - 1 - move_to_E.
            // We need 1 slot.
            // Is p_count - 1 - move_to_E >= 1?
            // => p_count - move_to_E >= 2.
            // Recall move_to_E = min(d, p_count_old) = min(d, p_count-1).
            // So p_count - min(d, p_count-1) >= 2?
            // If d is small, say d=0, then move_to_E=0. p_count >= 2 holds if we collected >= 2.
            // What if p_count is small? Or d is large?
            // If d >= p_count-1, then move_to_E = p_count-1.
            // Then p_count - (p_count-1) = 1.
            // 1 >= 1? Yes.
            // BUT wait, we need to move New to E.
            // Current E size = (m - p_count + 1) + (p_count - 1) = m.
            // E is FULL.
            // So we CANNOT move New to E.
            
            // Case E full: Happens when d >= p_count - 1.
            // In this case move_to_P = d - (p_count - 1).
            // P has [Old] [Bad2] [New].
            // We can't use E.
            // But we can use j!
            // j is missing d+1 balls. Space d+1.
            // We can dump P top to j.
            // Move New -> j.
            // Move Bad2 -> j.
            // Move Bad1 -> j.
            // j is restored (except New is deep, Bad on top).
            // Then fetch New from j again?
            // New is at depth 0 in j (since we pushed New, then Bad2, then Bad1).
            // Wait, last in first out.
            // Pushed New. Pushed Bad2. Pushed Bad1.
            // Top of j is Bad1. Then Bad2. Then New.
            // New is at depth d again!
            
            // We haven't made progress if we do this.
            // We need to permute New past Bad2.
            
            // Alternative:
            // P: [Old] [Bad2] [New].
            // E: [Junk] [Bad1].
            // We want P: [Old] [New]. E: [Junk]. j: [Rest] [Bad1] [Bad2].
            
            // We can move Bad1 from E -> j first?
            // Yes, E top is Bad1.
            // Move Bad1 -> j.
            // E is now [Junk]. Space available!
            // Space is p_count - 1.
            // Can we move New -> E?
            // If p_count - 1 >= 1 (i.e. p_count >= 2).
            // If p_count=1, space 0.
            
            // If p_count >= 2:
            // 1. Move Bad1 E->j.
            // 2. Move New P->E.
            // 3. Move Bad2 P->j.
            // 4. Move New E->P.
            // Done.
            
            // What if p_count=1? (We just collected the very first target from other poles).
            // P: [Target_New]. (Since Old is empty).
            // Actually, if Old empty, p_count=1 means we collected 1.
            // Wait, loop condition p_count < m.
            // Initial p_count could be 0?
            // No, we sorted P first.
            // If P had 0 targets initially, p_count=0.
            // Then move_to_E = min(d, 0) = 0.
            // move_to_P = d.
            // P: [Bad2] [New].
            // E: [Junk=all m balls]. E full.
            // Bad1 is empty.
            // We need to swap Bad2 and New.
            // E is full. No space.
            // We have only P and j.
            // P has Bad2 and New.
            // j has space.
            // Move New -> j.
            // Move Bad2 -> j.
            // j has [New] [Bad2].
            // Fetch New again.
            // New is at depth |Bad2|.
            // This is cycle.
            
            // However, p_count=0 case is special.
            // E has m balls (Junk).
            // But we don't need to keep Junk in E if p_count=0.
            // We can treat P as clean slate.
            // We cleared P (moved all to E).
            // So P is empty.
            // We fetch New.
            // Move d balls j -> P.
            // Move New j -> P.
            // P: [Bad2] [New].
            // We want [New].
            // Move New -> j? Cycle.
            // Move Bad2 -> E? E full.
            
            // Wait. If p_count=0, E has balls from P.
            // We can move balls from E -> j!
            // j has space d+1.
            // Move d balls from E -> j?
            // Then E has space d.
            // Then we can use E to sort P.
            // Move New P -> E.
            // Move Bad2 P -> E.
            // Move New E -> P.
            // Move Bad2 E -> j (or back to E).
            // Move d balls j -> E.
            
            // Logic for p_count=0:
            // 1. Fetch New from j:
            //    Move d balls j -> P.
            //    Move New j -> P.
            //    P: [Bad] [New].
            // 2. Make space in E.
            //    Move d+1 balls from E -> j. (Since j has space d+1).
            //    E has space d+1.
            // 3. Sort P using E.
            //    Move New P -> E.
            //    Move Bad P -> E.
            //    Move New E -> P.
            //    P: [New].
            //    E top: Bad. Below: Original Junk (minus d+1).
            // 4. Restore E and j?
            //    Bad is in E. We want it in j.
            //    Move Bad E -> j.
            //    Now we need to bring back the d+1 balls from j to E?
            //    Yes, to restore "Junk in E".
            //    Move d+1 balls j -> E.
            //    Done.
            
            // Generalized fix for any p_count:
            // P: [Old] [Bad2] [New].
            // E: [Junk] [Bad1].
            // We want P: [Old] [New].
            // Bad1 and Bad2 -> j.
            // New -> P.
            
            // Step A: Move Bad1 E -> j.
            // E: [Junk]. Space available = p_count + |Bad1| - |Bad1| = p_count (Wait? No).
            // E originally had m - (p_count-1) Junk + |Bad1|.
            // After removing Bad1, E has m - p_count + 1 balls.
            // Space = m - (m - p_count + 1) = p_count - 1.
            
            // If space >= 1 (p_count >= 2):
            //   Move New P -> E.
            //   Move Bad2 P -> j.
            //   Move New E -> P.
            
            // If space == 0 (p_count == 1):
            //   We have 1 Target in P (New).
            //   P: [Bad2] [New].
            //   E: [Junk]. (Size m).
            //   Bad1 was empty (since p_count=1, move_to_E=0).
            //   So Step A did nothing. E is full.
            //   Same logic as p_count=0?
            //   Actually here p_count=1 means P has 1 target (New).
            //   Wait, p_count was incremented. Old count was 0.
            //   So this IS the p_count=0 case logic.
            //   We need to free space in E.
            //   j has space |Bad2| + 1. (Since |Bad1|=0).
            //   Move balls from E -> j.
            //   ... Same sort logic ...
            //   Restore.
            
            if (p_count > 1) {
                // Standard case
                move_k(n, j, move_to_E); // Bad1 -> j
                move_k(target_pole, n, 1); // New -> E
                move_k(target_pole, j, move_to_P); // Bad2 -> j
                move_k(n, target_pole, 1); // New -> P
            } else {
                // p_count == 1 (First target collected)
                // P: [Bad2] [New]. E: Full Junk. Bad1 is empty.
                // j space: move_to_P + 1.
                int space_j = move_to_P + 1;
                // Move space_j balls E -> j
                move_k(n, j, space_j);
                
                // Now E has space space_j.
                // P -> E (New)
                move_k(target_pole, n, 1);
                // P -> E (Bad2)
                move_k(target_pole, n, move_to_P);
                // E -> P (New)
                move_k(n, target_pole, 1);
                // E -> j (Bad2)
                move_k(n, j, move_to_P);
                
                // Restore E (bring back space_j balls from j)
                move_k(j, n, space_j);
            }
        }
        
        // Finalize:
        // P is full of Targets.
        // E has Junk.
        // But Junk belongs to P (originally)?
        // No, we partitioned.
        // We need to empty E to proceed to next color.
        // E contains m Junk balls.
        // We can move them to any other pole?
        // Poles > target_pole are mixed.
        // Poles < target_pole are full/done.
        // P is full.
        // We need E empty.
        // Where to put Junk?
        // We extracted m Targets from system.
        // We displaced m Junk balls.
        // They should fill the holes left by Targets.
        // The holes are in poles j.
        // But we filled the holes with Bad balls back and forth.
        // Wait, every time we took a Target from j, we moved a Bad ball (from P's Junk) to j?
        // In my logic:
        //   Fetch: j -> P (Target).
        //   Restore: P -> j (Bad2), E -> j (Bad1).
        //   Wait. Bad1 and Bad2 came from j.
        //   So we returned the SAME balls to j.
        //   We took Target. We put back nothing?
        //   j has 1 empty slot?
        //   Yes!
        //   After fetching m Targets, we have m empty slots distributed across j's.
        //   We have m Junk balls in E.
        //   Distribute Junk to j's.
        
        for(int j = target_pole + 1; j < n; ++j) {
            while(poles[j].size() < m && poles[n].size() > 0) {
                move_k(n, j, 1);
            }
        }
    }

    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        cout << op.from << " " << op.to << "\n";
    }

    return 0;
}