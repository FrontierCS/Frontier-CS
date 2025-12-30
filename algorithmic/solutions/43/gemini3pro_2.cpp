#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    // Grid dimensions. N, M <= 100.
    // We choose N=42, M=42 to allow for a structured layout with 2x2 box.
    // The layout will be a series of rows.
    // Each "track" for the box will be 4 cells high (allowing a zig-zag).
    // Tracks are separated by walls.
    
    int N = 37; // Height
    int M = 55; // Width
    
    // Initialize grid with walls
    vector<string> grid(N, string(M, '#'));

    // Helper to clear a rectangle
    auto clear_rect = [&](int r, int c, int h, int w) {
        for(int i=r; i<r+h; ++i) {
            for(int j=c; j<c+w; ++j) {
                if(i >= 0 && i < N && j >= 0 && j < M)
                    grid[i][j] = '.';
            }
        }
    };

    // Construct a snake path for the box.
    // Box size is 2x2.
    // We use horizontal corridors of height 2 for the box to slide.
    // To force player movement, we can make the box zigzag or just simple path.
    // For reliability and solvability in a constructive algorithm, we use a simple snake
    // but narrow corridors so player interaction is constrained.
    
    // Corridors at rows: 2-3, 6-7, 10-11, ...
    // Spacing of 4 rows.
    // Walls at 0, 1, 4, 5, 8, 9...
    // Actually, we need wall thickness 1.
    // Rows 1-2: Box
    // Row 3: Wall
    // Rows 4-5: Box
    
    // Let's use a pattern where box moves in rows r, r+1.
    // Player access channel is row r-1 or r+2.
    
    int row_step = 4;
    int num_rows = (N - 2) / row_step;
    
    // Start position for Box
    int start_r = 2;
    int start_c = 2;
    
    // Goal position for Box
    int goal_r = 0;
    int goal_c = 0;
    
    // Carve the snake
    for(int i = 0; i < num_rows; ++i) {
        int r = 2 + i * row_step;
        // Clear box corridor
        // Leave 2 cols margin at ends for turning
        clear_rect(r, 2, 2, M-4);
        
        // Connect to next row
        if (i < num_rows - 1) {
            if (i % 2 == 0) {
                // Right turn
                clear_rect(r, M-4, 2 + row_step, 2); 
            } else {
                // Left turn
                clear_rect(r, 2, 2 + row_step, 2); 
                // Correction: the rect above goes down into next row
                // r is top of current. r + row_step is top of next.
                // Height needs to cover gap.
                // Gap is rows r+2, r+3.
                // Current r, r+1. Next r+4, r+5.
                // We need to clear r..r+5 roughly? 
                // clear_rect(r, 2, 6, 2) covers current(2)+gap(2)+next(2).
                // Actually we want just the turn.
            }
        }
    }

    // Fix the turns precisely
    for(int i = 0; i < num_rows; ++i) {
        int r = 2 + i * row_step;
        if (i < num_rows - 1) {
            // Gap is at r+2, r+3.
            if (i % 2 == 0) {
                // Connect Right: (r, M-4) to (r+4, M-4)
                // Clear rows r+2, r+3 at cols M-4, M-3
                clear_rect(r, M-4, row_step+2, 2); 
            } else {
                // Connect Left: (r, 2) to (r+4, 2)
                clear_rect(r, 2, row_step+2, 2);
            }
        }
    }
    
    // Carve Player Channels (The "Fins" or "Return Paths")
    // Rows r+2 is a wall currently.
    // We make it a narrow tunnel for player to move.
    // Box is 2x2. Box path is width 2.
    // Player needs to get around the box.
    // We add a parallel player track row r+2.
    
    for(int i = 0; i < num_rows; ++i) {
        int r = 2 + i * row_step;
        // Player track at r+2.
        // Needs to connect to box track to allow pushing.
        // We poke holes every few cells.
        // This makes "Fins".
        
        // Clear the player track line
        if (i < num_rows - 1) {
             // Row r+2
             // Don't clear strictly all, maybe leave some for walls
             // But for solvability, open is better.
             clear_rect(r+2, 2, 1, M-4);
        }
        
        // Add "ports" connecting box track (r+1) and player track (r+2)
        // Also box track (r) and above?
        // Box occupies r, r+1.
        // Player is at r+2 (below) or r-1 (above).
        // Let's clear r-1 as well.
        if (i > 0) {
             clear_rect(r-1, 2, 1, M-4);
        }
    }
    
    // Ensure connectivity between rows for player
    // The turns handle box connectivity. Player can use box turns.
    // But box might block turns.
    // Add dedicated player passages at ends.
    for(int i = 0; i < num_rows; ++i) {
        int r = 2 + i * row_step;
        // Left end passage
        clear_rect(r-1, 1, 6, 1);
        // Right end passage
        clear_rect(r-1, M-2, 6, 1);
    }

    // Place Box (B) at start of snake
    int br = 2; 
    int bc = 2;
    // P at start position
    // Box is 2x2 at (br, bc).
    grid[br][bc] = 'B'; grid[br][bc+1] = 'B';
    grid[br+1][bc] = 'B'; grid[br+1][bc+1] = 'B';
    
    // Place Player (P)
    // Place to the right of box to push it left? No, snake starts moving Right.
    // So player must be Left of box.
    grid[br][bc-1] = 'P';
    
    // Place Storage (S) at end of snake
    // Determine end coordinates
    int end_row_idx = num_rows - 1;
    int end_r = 2 + end_row_idx * row_step;
    int end_c;
    if (end_row_idx % 2 == 0) {
        end_c = M - 4; // Right side
    } else {
        end_c = 2; // Left side
    }
    
    // Ensure the storage area is clear of walls (it should be, due to box corridor)
    // Mark Storage
    // S is 2x2
    // If end_c is at M-4, indices are M-4, M-3.
    // grid[end_r][end_c] is '.', set to S.
    // We need to ensure it's empty '.' before setting 'S'. 
    // It should be cleared by loop.
    
    // Clear specifically to be safe
    clear_rect(end_r, end_c, 2, 2);
    
    grid[end_r][end_c] = 'S'; grid[end_r][end_c+1] = 'S';
    grid[end_r+1][end_c] = 'S'; grid[end_r+1][end_c+1] = 'S';
    
    // Output
    cout << N << " " << M << endl;
    for(const auto& row : grid) {
        cout << row << endl;
    }

    return 0;
}