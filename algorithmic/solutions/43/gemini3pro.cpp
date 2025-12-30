#include <iostream>
#include <vector>
#include <string>

using namespace std;

// Problem: Bigger Sokoban 40k
// Box: 2x2. Storage: 2x2.
// Grid size N x M (N+M <= 100).
// Strategy: 
// 1. Box moves in a ladder pattern (Left side of grid) with 4 steps per cycle (R, D, L, D).
// 2. Each step forces the player to reposition to a specific side (Left/Right/Top).
// 3. Player paths ("Ports") are routed to two separate bus networks (Bus A and Bus B).
// 4. Bus A and Bus B are connected ONLY via a long snake maze covering the rest of the grid.
// 5. Steps alternate requiring Bus A and Bus B, forcing a full maze traversal for every move.

// Grid Dimensions
const int N = 40;
const int M = 60;

char grid[N][M];

void draw_rect(int r, int c, int h, int w, char fill) {
    for(int i=r; i<r+h; i++) {
        for(int j=c; j<c+w; j++) {
            if (i >= 0 && i < N && j >= 0 && j < M)
                grid[i][j] = fill;
        }
    }
}

int main() {
    // Initialize with walls
    for(int i=0; i<N; i++) {
        for(int j=0; j<M; j++) {
            grid[i][j] = '#';
        }
    }

    // --- Bus System ---
    // Left Buses: Col 0 (A), Col 2 (B).
    // Right Buses: Col 12 (B), Col 14 (A).
    // Ladder Area: Cols 4..10.
    // Maze Area: Cols 15..M-1.

    // Clear vertical bus columns
    for(int i=1; i<N-1; i++) {
        grid[i][0] = '.'; // Left A
        grid[i][2] = '.'; // Left B
        grid[i][12] = '.'; // Right B
        grid[i][14] = '.'; // Right A
    }

    // Bus connections logic (Rows)
    // Left Side:
    // Even rows -> Bus B (Connect col 2 to ladder). Wall at col 1 (Block A).
    // Odd rows -> Bus A (Connect col 0 to ladder). Wall at col 3 (Block B).
    for(int i=1; i<N-1; i++) {
        if (i % 2 == 0) { // Even -> B
            grid[i][1] = '#'; 
            grid[i][3] = '.'; // Open to ladder
        } else { // Odd -> A
            grid[i][1] = '.'; // Connect 0 to 2
            grid[i][3] = '#'; // Block B
            grid[i][2] = '.'; // Pass through B col (bridge logic handled by logic below)
            // Wait, if grid[i][2] is part of Bus B, and we use it to cross for A?
            // We can't cross.
            // But Bus B is vertical.
            // We can break Bus B vertical connectivity at Odd rows?
            // Yes. Bus B vertical only at Even rows + connectors.
        }
    }

    // Fix Vertical Connectivity for Buses
    // Bus A (Col 0) is continuous.
    // Bus B (Col 2) is continuous? 
    // If Row i (Odd) uses Col 2 as a corridor for A, then Col 2 cannot be B at that cell.
    // So Bus B (Col 2) is only valid at Even rows.
    // To make Bus B connected, we need vertical segments at Col 2? 
    // No, we can route Bus B via Col 3? No.
    // Let's use Col 1 for A-crossing?
    // Better: 
    // Bus A: Col 0.
    // Bus B: Col 2.
    // Crossings:
    // Row Odd (for A): 0(.) 1(.) 2(.) 3(#).  --> 2 is part of path.
    // Row Even (for B): 0(#) 1(#) 2(.) 3(.). --> 2 is part of path.
    // So Col 2 is used by BOTH. This merges them. BAD.
    // We need 3D bridge. Not possible.
    // Alternative: Zig-zag buses.
    // Or simply route Bus B around?
    // We have enough columns.
    // Let's shift.
    // Left Buses: Col 0 (A), Col 1 (A-access), Col 2 (B), Col 3 (B-access).
    // Row Odd (Target A): Connect Ladder to Col 0 via Row Odd.
    //   Must cross Col 2.
    //   So Col 2 must NOT be B at Row Odd.
    //   So Bus B must snake? Or use gaps.
    //   If Bus B exists only at Even rows and connects vertically via Col 3?
    //   Yes. Col 2 is horizontal access for A (at Odd) and B (at Even)? No.
    
    // Revised Buses Left:
    // Col 0: Bus A (Vertical Spine).
    // Col 2: Bus B (Vertical Spine).
    // Connections from Ladder (Col 5):
    // Target A (Odd Row): 5->4->3->2->1->0.
    // Target B (Even Row): 5->4->3->2.
    // Conflict at Col 2.
    // Solution: Bus B uses Col 3 as spine?
    // If Bus B is Col 3.
    // Even Row: 5->4->3. (Connected).
    // Odd Row (Target A): 5->4->3->2->1->0.
    //   Must cross Col 3.
    //   So Col 3 cannot be Bus B at Odd Row.
    //   Bus B spine must be at Col 2?
    //   Then Even Row needs to reach Col 2. Crosses 3.
    //   It seems we always cross "Inner" to reach "Outer".
    //   Unless we alternate columns!
    //   Bus A at Col 0. Bus B at Col 2.
    //   Odd Row: 0..5 are Open. (A connected).
    //   Even Row: 2..5 are Open. 0..1 Blocked. (B connected).
    //   Vertical connectivity:
    //   Bus A (Col 0) vertical is clear.
    //   Bus B (Col 2) vertical must skip Odd rows (used by A).
    //   This disconnects B vertically.
    //   UNLESS we use Col 1 for B vertical?
    //   No, Row Odd at Col 1 is used by A.
    //   We need a Bypass for B.
    //   Can we route B to the side?
    //   No, A is at 0.
    //   Okay, route A to the side (Col -1 impossible).
    //   
    //   Let's use the top/bottom "Global" area to connect the disjoint vertical segments of B?
    //   No, too many segments.
    //   
    //   Wait, we only need connectivity to the Maze.
    //   Maze entry is A. Maze exit is B.
    //   We need all "A-ports" connected to Maze Entry.
    //   All "B-ports" connected to Maze Exit.
    //   
    //   Solution: Interleaved Vertical Lines.
    //   Col 0: Bus A.
    //   Col 1: Bus B.
    //   Rows for A-ports: 1, 5, 9... (1 mod 4).
    //   Rows for B-ports: 3, 7, 11... (3 mod 4).
    //   Then we have gaps!
    //   This reduces cycle density by 2. Acceptable (Score is high enough).
    //   
    //   Let's try:
    //   Rows $4k+1$: A-Left.
    //   Rows $4k+3$: B-Left.
    //   Cols:
    //   Col 0: Bus A Spine.
    //   Col 2: Bus B Spine.
    //   Row $4k+1$: Connect 5..0. (Cross 2).
    //     At $(4k+1, 2)$, we break Bus B vertical.
    //     Bus B vertical at Col 2 can wiggle to Col 3 at $4k+1$?
    //     Yes!
    //     Bus B: Vertical at Col 2. At row $4k+1$, shift to Col 3 (or 1).
    //     Col 1 is crossed by A? Yes. Col 3 is crossed by A? Yes.
    //     Basically A-row cuts through everything.
    //     
    //     Actually, just use separate planes? No.
    //     
    //     Backtrack: Right side buses are easy (A is outer, B is inner, or vice versa).
    //     Left side: A is outer (0), B is inner (2).
    //     We need to connect 5->0 (A) without breaking B.
    //     We need to connect 5->2 (B) without breaking A (A is far, so easy).
    //     The problem is A crossing B.
    //     
    //     Use vertical wiggle for B:
    //     B spine is Col 2.
    //     At A-row (Odd), B moves to Col 3?
    //     But A-row goes 5->0, so it uses 5,4,3,2,1,0.
    //     It cuts ALL columns.
    //     
    //     Okay, we cannot cross.
    //     We must route A-ports to the Left and B-ports to the Right?
    //     We have 2 Left Ports (A and B).
    //     We must route Left-B to Right-B via "under the ladder"?
    //     We can pass under the box track?
    //     Box Track uses Cols 6,7.
    //     Cols 4,5,8,9 are buffer.
    //     Can we route Left-B (Row $2k$) through Col 6?
    //     Only if Box is not there.
    //     Box is at $(2k+1, 6)$ during Push 4.
    //     Free cells at $(2k, 6)$?
    //     Yes.
    //     Can we go $(2k, 6) \to (2k, 7) \to (2k, 8) \to$ Right Bus B?
    //     $(2k, 7)$ is free?
    //     Box at $2k, 6$ (Push 1 starts) -> Occupies $(2k, 6), (2k, 7), (2k+1, 6), (2k+1, 7)$.
    //     So $(2k, 7)$ is blocked during Push 1.
    //     But we need path for Push 4.
    //     During Push 4, Box is at $(2k+1, 6)$.
    //     $(2k, 6)$ and $(2k, 7)$ are free.
    //     So yes! We can route Left-B to the Right Side through the ladder track!
    //     
    //     So:
    //     All B-ports connect to Right Bus B.
    //     All A-ports connect to Left Bus A.
    //     AND we need to route Right-A to Left-A?
    //     Right-A is at Row $2k+2$.
    //     Can we route through ladder?
    //     Box at $(2k+1, 7)$ (Push 3 starts). Occupies $(2k+1, 7)..(2k+2, 8)$.
    //     We need path from Right (Col 9) to Left (Col 5).
    //     Row $2k+2$: $(2k+2, 7)$ is blocked by Box.
    //     So cannot cross.
    //     
    //     Okay, we have 3 independent sets:
    //     Left-A, Left-B (routed to Right), Right-B, Right-A.
    //     We can merge Left-B and Right-B on the Right.
    //     We have Left-A and Right-A.
    //     Can we merge Right-A to Left-A?
    //     Global connection: Top Row and Bottom Row.
    //     Left Bus A (Col 0) connected to Top Row.
    //     Right Bus A (Col 14) connected to Top Row.
    //     Merged!
    //     
    //     So:
    //     Bus A = Col 0 + Col 14 + Top/Bottom Connectors.
    //     Bus B = Col 12 (Right side) + Left-B ports routed through ladder.
    //     
    //     Left-B Port is at Row $2k$. Pos $(2k, 6)$.
    //     Route: $(2k, 6) \to (2k, 7) \to (2k, 8) \to (2k, 9) \to$ Col 12.
    //     Is this path clear during Push 4?
    //     Push 4: Box at $(2k+1, 6)$.
    //     Rows $2k+1, 2k+2$.
    //     Row $2k$ is clear.
    //     Wait, previous box was at $(2k+1, 7)$ (Push 3).
    //     After Push 3 (L), box is at $(2k+1, 6)$.
    //     So Row $2k$ is strictly above current box.
    //     Is it blocked by Previous Previous Box?
    //     Game state is static for the path.
    //     Path must be valid *during* the move.
    //     Yes, Row $2k$ is empty.
    //     
    //     What about blocking Push 1?
    //     Push 1 Box at $(2k, 6)$.
    //     Occupies Row $2k$.
    //     So Row $2k$ is BLOCKED during Push 1.
    //     But we only need the path for Push 4.
    //     Correct.
    
    // Final Layout Plan:
    // Cols 0, 1: Bus A (Left).
    // Cols 2..9: Ladder. (Track at 6,7).
    // Cols 10, 11: Bus B (Right). (Actually Col 12).
    // Cols 12, 13: Bus A (Right). (Actually Col 14).
    // Maze 15+.
    
    // Buses:
    // Bus A: Col 0 (Left), Col 14 (Right). Connected via Row 0 and Row N-1.
    // Bus B: Col 12 (Right). 
    
    // Ladder Ports Routing:
    // Push 1 (Left A): Row $2k+1$. Connect $(2k+1, 5)$ to Col 0.
    // Push 2 (Right B): Row $2k-1$. Connect $(2k-1, 8)$ to Col 12.
    // Push 3 (Right A): Row $2k+2$. Connect $(2k+2, 9)$ to Col 14.
    // Push 4 (Left B routed to Right): Row $2k$. Connect $(2k, 6)$ -> Right -> Col 12.

    // Maze:
    // Connects Bus A (Col 14) to Bus B (Col 12).
    // Wait, Bus A is at 14, Bus B at 12.
    // They are adjacent.
    // We must block direct connection.
    // Wall at Col 13.
    // Maze starts at Col 14 (A). Ends at Col 12 (B).
    // The Maze fills the rest of the grid.
    
    // Draw Buses vertical lines
    for(int r=1; r<N-1; r++) {
        grid[r][0] = '.'; // Left A
        grid[r][14] = '.'; // Right A
        grid[r][12] = '.'; // Right B
    }
    // Global A Connectors
    for(int c=0; c<=14; c++) {
        grid[0][c] = '.';
        grid[N-1][c] = '.'; // Redundant but ok
    }
    // Isolate B (Col 12) from Global A
    grid[0][12] = '#'; 
    grid[N-1][12] = '#';
    // Isolate Left A (Col 0) from Ladder except at ports
    for(int r=1; r<N-1; r++) grid[r][1] = '#'; 
    // Isolate Right B (Col 12) from Ladder except at ports
    for(int r=1; r<N-1; r++) grid[r][11] = '#';
    // Isolate Right A (14) from Right B (12)
    for(int r=1; r<N-1; r++) grid[r][13] = '#';

    // Ladder Logic
    // Box Track cols 6, 7.
    // Wall Tube at 5 and 8.
    for(int r=2; r<N-2; r++) {
        grid[r][5] = '#';
        grid[r][8] = '#';
        grid[r][6] = '.';
        grid[r][7] = '.';
    }
    
    int cycles = (N - 4) / 2; // e.g. rows 2..N-3
    // Start Box Position: (2, 6)
    
    for(int k=0; k<cycles; k++) {
        int r_base = 2 + 2*k;
        // Push 1 (R): Row r_base. Target A (Left).
        // Port at (r_base+1, 5) -> 0.
        // Wall 5 is closed, need hole.
        grid[r_base+1][5] = '.';
        // Connect 5 to 0. (1 is wall, need hole).
        grid[r_base+1][1] = '.';
        // Clear path 2..4
        for(int c=2; c<=4; c++) grid[r_base+1][c] = '.';

        // Push 2 (D): Row r_base. (Box moves 6->7).
        // Player at Top (r_base-1, 7/8).
        // Port at (r_base-1, 8) -> Right B (12).
        // Wall 8 need hole.
        if (r_base-1 > 1) { // Check boundary
             grid[r_base-1][8] = '.';
             // Connect 8 to 12. (11 is wall).
             grid[r_base-1][11] = '.';
             for(int c=9; c<=10; c++) grid[r_base-1][c] = '.';
        }

        // Push 3 (L): Row r_base+1. (Box 7).
        // Player Right (r_base+1, 9) -> Right A (14).
        // Actually player at (r_base+2, 9)?
        // Box at (r_base+1, 7). Pushing Left.
        // Player needs to be at Right of Box.
        // Box occupies rows r_base+1, r_base+2.
        // Player at (r_base+1, 9) or (r_base+2, 9).
        // Use r_base+2.
        grid[r_base+2][8] = '.'; // Hole in tube
        grid[r_base+2][11] = '.'; // Hole in B-barrier? No, A is 14.
        // Wait, 11 blocks ladder from 12(B).
        // We need to reach 14(A).
        // Must cross 12(B).
        // Row r_base+2.
        // We open 11, 12, 13 at Row r_base+2.
        grid[r_base+2][11] = '.';
        grid[r_base+2][12] = '.'; // Crossing B spine
        grid[r_base+2][13] = '.';
        for(int c=9; c<=10; c++) grid[r_base+2][c] = '.';
        // Note: This breaks B vertical at r_base+2.
        // This is fine if B doesn't need vertical connectivity at this exact row.
        // B ports are at r_base-1 and r_base.
        // B vertical continuity needed?
        // B needs to connect to Maze Exit.
        // Maze Exit can be at bottom.
        // All B ports must reach bottom.
        // Breaks at r_base+2 might isolate B ports above?
        // We need to ensure B is connected.
        // B is broken at every r_base+2.
        // But B ports are at r_base and r_base-1.
        // They are adjacent to the break.
        // Can we route B around the break? Use col 10?
        grid[r_base+2][10] = '.'; 
        grid[r_base+2][12] = '#'; // Keep B spine intact?
        // If we block 12, we can't cross to 14.
        // So we MUST break 12.
        // Route B via 10 around the break?
        // At row r_base+2, B-spine (12) is broken.
        // We open (r_base+1, 10), (r_base+2, 10), (r_base+3, 10).
        // And connect 12->10 at r_base+1 and r_base+3.
        grid[r_base+1][10] = '.'; grid[r_base+1][12] = '.'; // Link
        grid[r_base+3][10] = '.'; grid[r_base+3][12] = '.'; // Link
        grid[r_base+2][10] = '.'; // Bypass
        // Now B flows 12 -> 10 -> 12 around row r_base+2.
        
        // Push 4 (D): Row r_base+1. Box moves 7->6.
        // Player at Top (r_base, 6).
        // Internal track port.
        // Connect (r_base, 6) -> Right -> B(12).
        // Path: (r_base, 6)->(r_base, 7)->(r_base, 8)->...->12.
        grid[r_base][8] = '.'; // Hole
        grid[r_base][11] = '.'; // Hole
        for(int c=6; c<=10; c++) grid[r_base][c] = '.';
    }

    // Maze Generation (Cols 15 to M-1)
    // Entry: A (14). Exit: B (12).
    // Connect 14 to Maze Start (Top Right).
    // Connect 12 to Maze End (Bottom Right).
    // Actually, simply:
    // Maze fills 15..M-1.
    // Entrance at Row 1 (from 14).
    // Exit at Row N-2 (to 12). (Route 12->14->Maze at bottom?) No 12 is blocked from 14.
    // Connect 12 to Maze at bottom directly?
    // 12 is B. 13 is wall. 14 is A.
    // At bottom, open 13? No, that merges A and B.
    // We need Maze to output to 12.
    // Maze can connect to 12 at any point.
    // Let's snake the maze.
    // Rows 1..N-2.
    // Snake: Left->Right, Down, Right->Left, Down.
    // Start at Top-Left of Maze (1, 15). Connected to 14 (A) via (1, 14).
    // End at Bottom-Left of Maze (N-2, 15). Connected to 12 (B)?
    // Problem: 12 is separated from 15 by 13(Wall) and 14(A).
    // We can't cross A to get to B.
    // We need to route B (12) under A?
    // Use Row N-1 (Global).
    // Row N-1 connects 12?
    // Earlier I said Row N-1 connects 14 (A).
    // Let's use Row 0 for A, Row N-1 for B.
    // Remove A from Row N-1.
    grid[N-1][12] = '.'; grid[N-1][14] = '#'; 
    for(int c=0; c<14; c++) grid[N-1][c] = '#'; // Clear N-1
    grid[N-1][12] = '.'; // B endpoint
    grid[N-1][13] = '.'; // Pass to maze?
    // If 13 is open, we need 14 closed.
    grid[N-1][14] = '#';
    // Connect Maze End (Bottom Right) to (N-1, 13)?
    // Maze cols 15..M-1.
    // Let's connect (N-1, 15) to (N-1, 13) -> (N-1, 12).
    
    // Check Global A at Row 0.
    // Connects 0 to 14. 
    // Isolate 12.
    grid[0][12] = '#';
    grid[0][13] = '.'; // 13 is A-connector at top?
    // Col 13 is wall 1..N-2.
    
    // Maze Snake
    for(int r=1; r<N-1; r+=2) {
        // Odd rows: 15 -> M-1
        for(int c=15; c<M; c++) grid[r][c] = '.';
        // Down connection at M-1
        if (r+1 < N-1) {
            grid[r+1][M-1] = '.';
            // Even rows: M-1 -> 15
            for(int c=M-1; c>=15; c--) grid[r+1][c] = '.';
            // Down connection at 15
            if (r+2 < N-1) grid[r+2][15] = '.';
        }
    }
    // Connect Entrance: (1, 15) to (1, 14).
    grid[1][14] = '.'; // A-bus to Maze
    
    // Connect Exit: Last Maze cell to B.
    // Last cell is near (N-2, 15) or (N-2, M-1).
    // If N is even (42), last row is N-2 (40, even).
    // Even rows go Right->Left (M-1 -> 15).
    // Ends at (N-2, 15).
    // Connect (N-2, 15) to (N-2, 12)?
    // Must cross 13, 14.
    // 13 is Wall, 14 is A.
    // Can't cross A.
    // Route via Row N-1.
    grid[N-2][15] = '.';
    grid[N-1][15] = '.'; // Down to N-1
    for(int c=15; c>=12; c--) grid[N-1][c] = '.'; // Path at bottom
    // Ensure A (14) is blocked at N-1.
    grid[N-1][14] = '#'; // Bridge B under A?
    // No, Row N-1 is strictly B.
    // A (Col 14) stops at N-2.
    grid[N-1][14] = '.'; // Used for B path
    // Col 14 vertical A must NOT connect to N-1.
    grid[N-2][14] = '.'; // A is here
    // Break A at N-2?
    // A needs to reach all ports. Lowest port is N-3 or so.
    // So blocking A at N-1 is fine.
    // But (N-1, 14) is '.', part of B path.
    // (N-2, 14) is '.', part of A bus.
    // They are adjacent vertically! Merge!
    // Wall at (N-2, 14) or (N-1, 14)?
    // Can't put wall, need path.
    // Shift B-exit path to Row N-1?
    // Use Col 13 for B-exit vertical drop?
    // Col 13 is wall.
    // Open 13 at bottom.
    // (N-2, 15) -> (N-2, 13)? Cross 14(A). Impossible.
    
    // Solution:
    // Flip Maze direction?
    // Or move Buses.
    // Put B at 14, A at 12?
    // Then Exit B is at edge, easy to connect.
    // Entry A is inner, crosses B?
    // Top connection for A (12) crosses B (14)?
    // Row 0: 0..12..14.
    // If A is 12, B is 14.
    // 0..12 is A. 14 is B.
    // 13 is barrier.
    // Row 0 crosses 13? No.
    // Row 0 connects Left A (0) to Right A (12).
    // Right B (14) is isolated.
    // Maze Entry A (12) -> Inner.
    // Maze Exit B (14) -> Outer.
    // Start Maze at (1, 15) connected to 14? No connected to 12.
    // (1, 12) -> (1, 13) -> (1, 14) -> (1, 15).
    // Crosses B(14).
    // So B(14) must have gap at Row 1.
    // B starts at Row 2?
    // Highest B-port is at Row 1 (Push 2, r_base=2 -> 2-1=1).
    // So B needs Row 1.
    // Can we start Maze at Row 3?
    // Lose space? Tiny.
    // Start Maze at Row 3.
    // Route A (12) -> Maze at Row 3. (Cross B at Row 3).
    // Break B at Row 3. Bypass B via Col 15?
    // Yes.
    
    // Apply Swap: Right A=12, Right B=14.
    // A ports use 12. B ports use 14.
    // Update logic above.
    // R-A port (Push 3, r+2) -> 12.
    // R-B port (Push 2, r-1) -> 14.
    // B-crossing for A-port connection:
    // A (12) is Inner. B (14) is Outer.
    // A port is at 9. Path 9->12 is direct.
    // B port is at 8. Path 8->14 crosses 12(A) and 13(Wall).
    // Need to cross A.
    // Break A at Row r-1. Bypass via 10/11?
    // Yes.
    
    // This swapping logic is getting complex.
    // Let's stick to original A=14, B=12.
    // Fix Exit merge.
    // Maze Exit at (N-2, 15). B is 12. A is 14.
    // Route B via Row N-1.
    // Problem: (N-2, 14)(A) touches (N-1, 14)(B path).
    // Insert Wall at (N-2, 14)?
    // Can we end A higher?
    // Lowest A-port?
    // Max cycle k. r_base = 2+2k.
    // Push 3 A-port at r_base+2.
    // Max row = 2 + 2*(cycles-1) + 2 = 2k_max + 2.
    // If N=42. Cycles=19. Max Row = 40 = N-2.
    // So A extends to N-2.
    // Conflict is real.
    
    // Fix:
    // End Maze at Col 13?
    // No.
    // Use Col 13 as B-Bus?
    // A at 14, B at 13.
    // Too tight.
    
    // Easy fix:
    // Stop Ladder 1 cycle early.
    // A ends at N-4.
    // Gap at N-3, N-2 allows crossing.
    cycles--; 
    
    // Placement
    grid[2][6] = 'B'; grid[2][7] = 'B';
    grid[3][6] = 'B'; grid[3][7] = 'B';
    grid[2][5] = 'P';
    grid[N-3][6] = 'S'; grid[N-3][7] = 'S';
    grid[N-2][6] = 'S'; grid[N-2][7] = 'S';

    // Output
    cout << N << " " << M << endl;
    for(int i=0; i<N; i++) {
        for(int j=0; j<M; j++) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    return 0;
}