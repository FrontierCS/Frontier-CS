#include <iostream>
#include <vector>
#include <string>

using namespace std;

// Grid size
const int N = 48;
const int M = 48;
char grid[N][M];

int main() {
    // Initialize grid with walls
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            grid[i][j] = '#';
        }
    }

    // Box path definition: Zigzag along the diagonal
    // Box Top-Left coordinates
    vector<pair<int, int>> box_path;
    int k = 2;
    while (k < N - 4) {
        // Current pos (k, k)
        box_path.push_back({k, k});
        // Move Right to (k, k+1)
        box_path.push_back({k, k+1});
        // Move Down to (k+1, k+1)
        // Next iteration handles (k+1, k+1) as the start of next cycle
        k++;
    }
    box_path.push_back({k, k}); // Final position

    // Carve Box Path
    for (auto p : box_path) {
        int r = p.first;
        int c = p.second;
        grid[r][c] = '.';
        grid[r][c+1] = '.';
        grid[r+1][c] = '.';
        grid[r+1][c+1] = '.';
    }

    // Carve A-Corridor (Left side access)
    // Runs parallel to diagonal on the lower-left side
    // Access points are at (r, c-1) and (r+1, c-1) for box at (r, c)
    // We connect them all into a single corridor along the diagonal
    for (int i = 2; i < N - 4; ++i) {
        // For box at (i, i), left is (i, i-1) and (i+1, i-1)
        // For box at (i, i+1), left is (i, i) - occupied, and (i+1, i) - occupied?
        // Wait, box at (i, i+1) occupies (i, i+1)..(i+1, i+2). Left is (i, i) and (i+1, i).
        // (i, i) was previous box pos, so it's empty.
        
        // We need a continuous corridor for the player to walk back to the start.
        // Let's carve a strip at c = r - 2?
        // (i, i-2) and (i+1, i-1)?
        // Let's be explicit.
        if (i-1 >= 0) grid[i][i-1] = '.'; // Adjacent to box
        if (i-1 >= 0) grid[i+1][i-1] = '.'; // Adjacent to box
        
        // The "Main A-Corridor" running back to start
        if (i-2 >= 0) grid[i][i-2] = '.';
        if (i-2 >= 0) grid[i+1][i-2] = '.';
    }
    
    // Carve B-Corridor (Top side access)
    // Runs parallel to diagonal on the upper-right side
    for (int i = 2; i < N - 4; ++i) {
        // Top access for box at (i, i): (i-1, i), (i-1, i+1)
        if (i-1 >= 0) grid[i-1][i] = '.';
        if (i-1 >= 0) grid[i-1][i+1] = '.';
        
        // The "Main B-Corridor"
        if (i-2 >= 0) grid[i-2][i] = '.';
        if (i-2 >= 0) grid[i-2][i+1] = '.';
    }

    // Carve Maze A (Lower Left Triangle)
    // Area defined roughly by r > c + 3
    // Entry at (2, 0) (connected to start of A-Corridor)
    // Exit at (N-1, M-1) (The Bridge)
    
    // Actually, simply snake the LL region.
    // Connect (4, 1) to A-Corridor near start.
    // Connect End of Snake to (N-1, 1).
    // Bridge connects (N-1, 1) to (N-1, M-1) along bottom edge?
    
    // Let's implement specific snake for A.
    // Rows 4 to N-2. Columns 1 to r-4.
    for (int r = 4; r < N-1; ++r) {
        int max_c = r - 4;
        if (max_c < 1) continue;
        for (int c = 1; c <= max_c; ++c) {
            grid[r][c] = '.';
        }
        // Connect rows
        if (r < N-2) {
            int next_max_c = r + 1 - 4;
            if (r % 2 == 0) {
                // End at right, connect to below
                grid[r][max_c] = '.'; // Already done
                grid[r+1][max_c] = '.'; // Down connection
            } else {
                // End at left, connect to below
                grid[r][1] = '.';
                grid[r+1][1] = '.';
            }
        }
    }
    
    // Connect A-Corridor Start to Maze A Start
    // A-Corridor start is around (2, 0) or (2, 1).
    // Grid[2][0] is valid.
    grid[2][0] = '.';
    grid[3][0] = '.';
    grid[4][0] = '.'; // Enters row 4 maze (starts at c=1, so connect (4,0) to (4,1))
    grid[4][1] = '.';

    // Connect A-Corridor to (2, 0)
    grid[2][0] = '.';
    if (grid[2][1] == '#') grid[2][1] = '.'; // Ensure connection

    // Ensure A-Corridor is NOT connected to Maze A anywhere else.
    // A-Corridor is at c = r-1, r-2.
    // Maze A ends at c = r-4.
    // Gap of 2 walls (cols r-3, r-2... wait).
    // If A-Corridor uses r-2, and Maze uses r-4. Gap is column r-3. Wall. Good.

    // Maze A Exit: Bottom row of maze (N-2).
    // Snake ends at (N-2, 1) or (N-2, max).
    // Check parity.
    // If N=48. Start row 4. Row 4 (even) goes Right. 5 Left. ...
    // Row 46 (even) goes Right. Ends at (46, 42).
    // Connect (46, 42) to Bridge.
    
    // Bridge: Path along bottom edge and right edge to top.
    // Let's put Bridge connection at (N-1, M-1).
    // Path from (46, 42) to (N-1, M-1).
    for (int c = 42; c < M; ++c) grid[46][c] = '.';
    for (int r = 46; r < N; ++r) grid[r][M-1] = '.';

    // Maze B (Upper Right Triangle)
    // Area c > r + 3.
    // Connect Maze B Start to Bridge at (N-1, M-1).
    // Connect Maze B End to B-Corridor Start near (0, 2).
    
    // Snake columns? Or rows?
    // Let's snake rows again for symmetry.
    // Rows 1 to N-5. Cols r+4 to M-2.
    for (int r = 1; r < N-4; ++r) {
        int min_c = r + 4;
        if (min_c >= M-1) continue;
        for (int c = min_c; c < M-1; ++c) {
            grid[r][c] = '.';
        }
        // Connect rows
        if (r < N-5) {
            int next_min_c = r + 1 + 4;
            if (r % 2 != 0) { // Start odd
                // Row 1 goes Right. End at M-2. Connect down.
                grid[r+1][M-2] = '.';
            } else {
                // Row 2 goes Left. End at min_c. Connect down?
                // Be careful with min_c shifting.
                // Row 2 min_c = 6. Row 3 min_c = 7.
                // Connect (2, 6) to (3, 6)? No, (3,6) is wall.
                // Connect (2, 7) to (3, 7).
                if (min_c + 1 < M-1) grid[r+1][min_c+1] = '.'; // Connect
                else grid[r+1][M-2] = '.'; // Fallback
            }
        }
    }
    
    // Connect Bridge (N-1, M-1) to Maze B Start.
    // Maze B bottom row is around r=43?
    // r < N-4 = 44. Last row 43.
    // Row 43 (odd) goes Right. Ends at M-2.
    // Connect (43, M-2) to (N-1, M-1).
    for (int r = 43; r < N; ++r) grid[r][M-2] = '.';
    grid[N-1][M-2] = '.'; 
    grid[N-1][M-1] = '.'; // Connect to bridge point

    // Connect Maze B End to B-Corridor Start.
    // Maze B top row is 1.
    // Row 1 goes Right. Starts at min_c = 5.
    // Connect (1, 5) to B-Corridor Start.
    // B-Corridor start is around (0, 2).
    // Path from (1, 5) to (0, 2).
    for (int c = 2; c <= 5; ++c) grid[0][c] = '.';
    grid[1][5] = '.';
    grid[0][5] = '.';
    
    // Ensure B-Corridor is NOT connected to Maze B elsewhere.
    // B-Corridor is c=r+1, r+2.
    // Maze B is c >= r+4. Gap c=r+3. Wall. Good.

    // Place Objects
    // Player Start: (2, 0) inside A-Corridor start.
    grid[2][0] = 'P';
    
    // Box Start: (2, 2)
    grid[2][2] = 'B'; grid[2][3] = 'B';
    grid[3][2] = 'B'; grid[3][3] = 'B';
    
    // Storage: Final pos of path
    int fk = box_path.back().first;
    int fc = box_path.back().second;
    
    // Clear any previous marks at storage to avoid overwrite issues?
    // But we write S over it.
    grid[fk][fc] = 'S'; grid[fk][fc+1] = 'S';
    grid[fk+1][fc] = 'S'; grid[fk+1][fc+1] = 'S';

    // Output
    cout << N << " " << M << endl;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }

    return 0;
}