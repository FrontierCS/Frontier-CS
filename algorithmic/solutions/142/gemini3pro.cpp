#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Operations storage
vector<pair<int, int>> moves;

// State
int n, m;
vector<vector<int>> poles;

// Perform a move
void move_ball(int x, int y) {
    if (poles[x].empty()) return; // Should not happen based on logic
    int ball = poles[x].back();
    poles[x].pop_back();
    poles[y].push_back(ball);
    moves.push_back({x + 1, y + 1});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    poles.resize(n + 2); // 0-indexed, but pole n+1 is index n.
    // Input uses 1-based colors. We keep them as is.

    for (int i = 0; i < n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }
    // Pole n is initially empty (the (n+1)-th pole)

    // Strategy:
    // Sort colors 1 to n-1 into poles 0 to n-2.
    // The last pole (n-1) will naturally contain color n.
    
    // We use pole n (the empty one) as a buffer.
    
    for (int target_color = 1; target_color < n; ++target_color) {
        int target_pole = target_color - 1;
        
        // Step 1: Count how many balls of target_color are in the target_pole.
        // Actually, we want to clear target_pole completely first to sort into it cleanly.
        // But we can't just clear it if others are full.
        // We use the "Batch Swap" logic with deadlock resolution.
        
        // Move all contents of target_pole to buffer_pole (index n).
        // target_pole becomes empty. buffer_pole becomes full.
        int buffer_pole = n;
        while (!poles[target_pole].empty()) {
            move_ball(target_pole, buffer_pole);
        }
        
        // Now target_pole is empty. buffer_pole contains the initial balls of target_pole.
        // We iterate through all other poles (including buffer_pole) to extract target_color.
        // The source poles are: buffer_pole, and all poles from target_pole + 1 to n-1.
        // Note: poles 0 to target_pole-1 are already sorted and should not be touched.
        
        // We treat buffer_pole as a source.
        // For other sources j, we perform the extraction.
        
        // Since buffer_pole is one of the sources but also acts as the buffer for non-target balls
        // during the swap process with other poles, we need to be careful.
        // Actually, the previous logic was: target_pole is destination for Color C.
        // Source j (mixed). Buffer E (starts full of mixed).
        
        // Let's implement the processing of each source j.
        for (int j = target_pole + 1; j < n; ++j) {
            // If j is the buffer pole, we skip for now? No, the buffer_pole is index n.
            // Wait, the loop j goes up to n-1. The buffer is n.
            // We need to process balls in buffer (index n) as well.
            // But the logic is: "Swap Batch" between Buffer and Pole j.
            // Buffer is E. Pole j is j.
            // Target is target_pole.
            
            // However, we first need to ensure Buffer (n) doesn't contain target_color?
            // No, we want to extract target_color from j AND from Buffer.
            
            // Let's run the algorithm for source j using Buffer n.
            // During this, we extract C to target_pole.
            // Non-C from j go to Buffer.
            // If Buffer is full and blocked, dump to target_pole (temporary garbage).
            
            int count_C_extracted = 0;
            // We need to extract all C from j.
            // We can count them first.
            int balls_in_j = poles[j].size();
            int c_in_j = 0;
            for(int val : poles[j]) if(val == target_color) c_in_j++;
            
            // We loop until we extracted all c_in_j
            int extracted_so_far = 0;
            
            while (extracted_so_far < c_in_j) {
                // Check tops
                int top_buf = poles[buffer_pole].back();
                int top_j = poles[j].back();
                
                bool buf_is_C = (top_buf == target_color);
                bool j_is_C = (top_j == target_color);
                
                if (buf_is_C) {
                    move_ball(buffer_pole, target_pole);
                    // Space opens in buffer
                } else if (!j_is_C) {
                    // Try to move j -> buffer
                    if (poles[buffer_pole].size() < m) {
                        move_ball(j, buffer_pole);
                    } else {
                        // Deadlock: Buffer full of non-C, j top is non-C.
                        // Must dump buffer top to target_pole to make space.
                        move_ball(buffer_pole, target_pole); 
                    }
                } else {
                    // top_j is C.
                    if (!buf_is_C) { // top_buf is non-C
                         // Perfect swap if space?
                         // We want j -> target_pole.
                         // But we might need to buffer non-C from j later?
                         // Actually, just move j -> target_pole.
                         move_ball(j, target_pole);
                         extracted_so_far++;
                         // Now we have space in j? No, j size decreased.
                         // We want to fill j with non-C from buffer.
                         move_ball(buffer_pole, j);
                    } else {
                        // Both are C. Handled by first if.
                    }
                }
            }
        }
        
        // After processing all j from target_pole+1 to n-1:
        // We still have the Buffer (n) itself which might contain target_color.
        // We need to move those to target_pole.
        // But target_pole might contain garbage (dumped during deadlocks).
        // And Buffer contains mixed non-C and maybe C?
        // Wait, did we process Buffer for C?
        // In the loop above, we only extracted C from Buffer if it was on top.
        // We didn't explicitly dig Buffer.
        
        // So now we must clean up Buffer and target_pole.
        // target_pole has: [Pure C] ... [Garbage] ... [Pure C] mixed.
        // Buffer has: [Non-C] ... [C] ... mixed.
        // AND j poles are full of non-C (mostly).
        
        // Actually, we want target_pole to be pure.
        // Let's filter target_pole and Buffer.
        // We can use a processed pole j (which has non-C) as helper? No it's full.
        
        // Better: We empty Buffer into target_pole completely?
        // No, target_pole capacity m.
        
        // Let's use the standard sort since we have only 2 poles of interest: target_pole and Buffer.
        // All C balls are in target_pole + Buffer.
        // All balls in target_pole + Buffer are either C or Non-C.
        // Total C = m.
        // Total balls in these two = K.
        // We want target_pole to have m balls of C.
        // Buffer to have K-m balls of Non-C.
        
        // Algorithm to partition 2 poles (A, B) using no extra space?
        // We have A (target_pole) and B (buffer).
        // A has some stuff, B has some stuff.
        // We can move B->A until A full.
        // Then move A->B?
        // This is "Selection Sort" on stack.
        // Count C in B. Move that many non-C from A to B?
        // We can do this because we have empty space = total capacity - total balls.
        // Since we processed j, j are full.
        // Total balls in A+B = 2m. Capacity = 2m.
        // So A is full, B is full?
        // Yes.
        
        // So we have 2 full poles A, B. We want to swap C from B to A, non-C from A to B.
        // Since we have no empty space, we are stuck?
        // No, we have the "deadlock dump" which implies A had space.
        // BUT at the end of loop, we filled j.
        // So A+B have 2m balls.
        
        // Wait, if we have 2 full poles and need to swap, we need a 3rd pole.
        // We can use a pole j?
        // j has non-C.
        // We can move one non-C from j to A (impossible A full).
        
        // Okay, use the "QuickSort" idea locally on A and B?
        // No space.
        // BUT we know A contains C's and B contains C's.
        // Total C = m.
        // If we simply check tops?
        // If Top(A) is non-C and Top(B) is C: Swap?
        // Can't swap directly without space.
        
        // RESTART STRATEGY for cleanup:
        // We shouldn't have filled j completely!
        // We should have kept space in Buffer.
        // Buffer capacity m.
        // When processing j, we move C to target. Non-C to Buffer.
        // If Buffer full, we move to target (garbage).
        // AFTER processing j, we should put back non-C from Buffer to j?
        // Yes! To free Buffer.
        // In the loop `while (extracted_so_far < c_in_j)`:
        // After extracting a C (and placing a non-C in j), j has m balls?
        // In my code: `move_ball(j, target_pole); move_ball(buffer_pole, j);`.
        // j size stays m.
        // So Buffer size stays same.
        // So Buffer space is constant.
        
        // So Buffer stays full (or near full).
        // We need to liberate space.
        // We can assume we started with empty target_pole, full Buffer.
        // target_pole filled with C and garbage.
        // Buffer filled with non-C.
        // At the end, target_pole + Buffer contains all C (m balls) + other non-C.
        // We want to sort them.
        // Since we processed all j, j are fine (no C).
        // We just need to fix A (target) and B (buffer).
        // A and B contain exactly m balls of C and m balls of non-C.
        // We want A to be all C, B to be all non-C.
        // BUT we have no extra space.
        // However, we can use a pole j as temporary storage.
        // j is full of non-C.
        // Move one ball from j to A? No A full.
        
        // The only way is if we did NOT fill j completely.
        // Or if we use the Generous Limit to unpack j.
        // Move all j to A? (A must be empty).
        
        // Correct fix:
        // When cleaning up A and B.
        // We iterate k from target_pole+1 to n-1.
        // We can swap one non-C from B with non-C from k? Useless.
        
        // What if we maintain B (Buffer) having 1 empty slot?
        // We can't if we have 2m balls.
        // But we have (n+1)m capacity.
        // n*m balls.
        // So we ALWAYS have m empty slots globally.
        // Since we processed j, j are full.
        // So A + B has m balls total??
        // Wait. n*m balls.
        // We have sorted 0..target_pole-1. (target_pole poles).
        // We processed j..n-1. (n - 1 - target_pole poles).
        // Total processed poles = n - 1.
        // Remaining poles: A and B.
        // Total balls = n*m.
        // Processed balls = (n-1)*m.
        // Remaining balls = m.
        // A + B share m balls.
        // Capacity A+B = 2m.
        // SO WE HAVE m EMPTY SLOTS!
        // A and B are NOT both full.
        // Combining A and B gives m balls.
        // One of them can hold ALL the balls.
        // So we can trivially sort!
        
        // Example: A has mix, B has mix. Total balls = m.
        // Move all B to A.
        // Now B is empty. A has m balls.
        // A contains all C balls (m of them) plus 0 non-C?
        // Wait. Total balls of color target_color = m.
        // So A must contain exactly all m balls of C.
        // And 0 non-C.
        // So A is sorted automatically!
        
        // Let's verify ball counts.
        // We extracted C from j. We put non-C into j.
        // Did we maintain j size = m?
        // Yes, `move_ball(j, target); move_ball(buffer, j)`.
        // So all j are full.
        // All previous sorted poles are full.
        // So A + B contains exactly m balls.
        // And since all C balls are in A+B, and total C = m,
        // Then A+B contains exactly m balls of color C.
        // So A+B contains ONLY balls of color C.
        // So we just move all from B to A.
        // Done.
        
        // Wait, did we put non-C back into j?
        // In the loop: `move_ball(buffer_pole, j)`.
        // We took non-C from buffer and put into j.
        // So yes, j is full of non-C.
        // This implies Buffer loses non-C.
        // Eventually Buffer only has C (and maybe some non-C if we dumped garbage).
        // But we dumped garbage to target_pole.
        // So Buffer + target_pole contains the C balls.
        
        // So yes: simply consolidate A and B into A.
        while (!poles[buffer_pole].empty()) {
            move_ball(buffer_pole, target_pole);
        }
        // Now target_pole has m balls (all C).
        // Buffer is empty.
        // Ready for next color.
    }
    
    // Output
    cout << moves.size() << "\n";
    for (const auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}