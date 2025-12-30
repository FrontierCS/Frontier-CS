#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int N = 50;
    int M = 50;
    
    // Initialize grid with walls
    vector<string> grid(N, string(M, '#'));
    
    // 1. Carve Vertical Corridors
    // Col 0: Left Hub (Left Corridor)
    // Col 6: Right Hub (Right Corridor)
    for (int r = 0; r < N; ++r) {
        grid[r][0] = '.'; 
        grid[r][6] = '.'; 
    }
    
    // 2. Carve Snake in cols 7..49
    // The Snake creates a very long path between the Left Hub and Right Hub.
    // Row 0 Connects Col 0 to Snake Start.
    // Row N-1 Connects Snake End to Col 6.
    
    // Connection at Top (Row 0)
    for (int c = 1; c <= 7; ++c) grid[0][c] = '.';
    
    // Connection at Bottom (Row 49)
    for (int c = 6; c < M; ++c) grid[N-1][c] = '.';
    grid[N-2][M-1] = '.'; // Connect last snake row to bottom row

    // Snake Body (Rows 1 to 48)
    for (int r = 1; r < N - 1; ++r) {
        if (r % 2 != 0) { 
            // Odd rows: Left to Right (7 -> 49)
            for (int c = 7; c < M; ++c) grid[r][c] = '.';
            if (r < N - 2) grid[r][M-1] = '.'; // Drop down
        } else { 
            // Even rows: Right to Left (49 -> 7)
            for (int c = M - 1; c >= 7; --c) grid[r][c] = '.';
            if (r < N - 2) grid[r][7] = '.'; // Drop down
        }
    }
    // Connect Row 0 to Row 1 start of snake
    grid[0][7] = '.';
    grid[1][7] = '.';

    // 3. Carve Box Path and Mechanism Gates
    // We create 15 cycles of the pattern.
    int num_cycles = 15;
    int start_row = 2;
    
    // Special access for the very first "Push Down" requirement at Row 1
    // Connects Left Hub to (1,3)
    grid[1][1] = '.';
    grid[1][2] = '.';
    grid[1][3] = '.';
    
    for (int i = 0; i < num_cycles; ++i) {
        int r = start_row + i * 3;
        // Each cycle occupies rows r, r+1 (Active) and r+2 (Buffer)
        
        // Clear the box channel (Cols 2, 3) and player areas (Col 4)
        for (int rr = r; rr <= r+2; ++rr) {
            grid[rr][2] = '.';
            grid[rr][3] = '.';
            grid[rr][4] = '.';
        }
        
        // Place Gates
        // Gate Left at (r, 1): Allows access from Left Hub for Push Right
        grid[r][1] = '.';      
        
        // Gate Right at (r+1, 5): Allows access to Right Hub for Push Left
        grid[r+1][5] = '.';    
        
        // Buffer Row Walls
        // We intentionally leave (r+2, 1) and (r+2, 5) as Walls '#' to prevent leaks.
        // We also explicitly set (r+2, 4) to Wall to prevent Right-side leakage.
        grid[r+2][4] = '#';
    }
    
    // Clear area for final box position (47, 2)
    // The loop covers clearing up to row 46.
    // The final box position occupies rows 47 and 48.
    for (int rr = 47; rr <= 48; ++rr) {
        grid[rr][2] = '.';
        grid[rr][3] = '.';
    }
    
    // 4. Place Entities
    // Player starts at (2, 1)
    grid[2][1] = 'P';
    
    // Box starts at (2, 2) (2x2)
    grid[2][2] = 'B'; grid[2][3] = 'B';
    grid[3][2] = 'B'; grid[3][3] = 'B';
    
    // Storage Target at (47, 2) (2x2)
    int tr = 47, tc = 2;
    grid[tr][tc] = 'S'; grid[tr][tc+1] = 'S';
    grid[tr+1][tc] = 'S'; grid[tr+1][tc+1] = 'S';
    
    // Output
    cout << N << " " << M << endl;
    for (const auto& s : grid) {
        cout << s << endl;
    }
    
    return 0;
}