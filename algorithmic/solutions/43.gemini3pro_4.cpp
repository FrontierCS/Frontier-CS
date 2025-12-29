#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int N = 50;
    int M = 50;
    
    // Initialize grid with walls
    vector<string> grid(N, string(M, '#'));
    
    // Build the Box Path (Staircase)
    // Box starts at (2, 2). Moves Right to (2,3), Down to (3,3), then repeat.
    // Logic coordinates: (r, c) refers to top-left of box.
    // Sequence: (2,2) -> (2,3) -> (3,3) -> (3,4) -> (4,4) ...
    // until we reach storage.
    
    vector<pair<int, int>> path;
    int r = 2, c = 2;
    path.push_back({r, c});
    while (r < 44 && c < 44) {
        // Move Right
        c++;
        path.push_back({r, c});
        // Move Down
        r++;
        path.push_back({r, c});
    }
    
    // Carve Box Path
    for (auto p : path) {
        int br = p.first;
        int bc = p.second;
        // 2x2 box area
        grid[br][bc] = '.';
        grid[br][bc+1] = '.';
        grid[br+1][bc] = '.';
        grid[br+1][bc+1] = '.';
    }
    
    // Rails and Hubs
    // Rail E (Top/Right access)
    // Rail S (Bottom/Left access)
    
    // We carve out specific access points and connect them to main hubs
    // Access points are adjacent to the box path cells
    
    // For each step in the path:
    // If move was Right (prev -> curr):
    //   Player pushed from Left. Access point: (curr.r, curr.c-1) and (curr.r+1, curr.c-1)
    //   These should connect to S-Hub.
    // If move was Down (prev -> curr):
    //   Player pushed from Top. Access point: (curr.r-1, curr.c) and (curr.r-1, curr.c+1)
    //   These should connect to E-Hub.
    
    // Also, the INITIAL position needs Left access (start push is Right).
    // The FINAL position is Storage.
    
    // Carve Rails
    for (size_t i = 1; i < path.size(); ++i) {
        int pr = path[i-1].first;
        int pc = path[i-1].second;
        int cr = path[i].first;
        int cc = path[i].second;
        
        if (cc > pc) { // Moved Right
            // Req Left access
            // Player stands at (cr, cc-1) and (cr+1, cc-1)
            // Note: (cr, cc-1) is (cr, pc). This was occupied by box in prev step?
            // Yes. Box at (pr, pc) occupied (pr, pc).
            // Now box at (cr, cc), (pr, pc) is free.
            // We ensure it connects to S-Hub.
            // Actually, we just need to ensure the "Left" side of the track is open to S-Hub
            // and "Top" side is open to E-Hub.
            
            // Just carve a dedicated rail line if possible.
            // But cells are tight.
            // We will carve S-Hub in the lower-left empty region and connect to the diagonal track from below.
            // We carve E-Hub in upper-right and connect from above.
        }
    }
    
    // Carve Diagonal Interface for Rails
    // For the staircase path, we need to open cells adjacent to the track.
    // S-Rail: (r+1, c) for the "Down" phase acts as future S-point?
    // Let's just open a 1-wide strip below and above the 2-wide box track diagonal.
    
    // The box track roughly occupies diagonal band.
    // Let's aggressively clear the S-Hub area (Lower Left) and E-Hub area (Upper Right)
    // but leave a wall buffer.
    
    // E-Hub / Upper Maze
    // Region: r < c - 2 roughly.
    // S-Hub / Lower Maze
    // Region: r > c + 2 roughly.
    
    // Generate Upper Maze (Serpentine)
    // Rows 0..48. Restrict columns to be > r + 3.
    // Start of Maze connected to E-Rail spots.
    // End of Maze connected to Lower Maze via tunnel.
    
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            // Check if (i, j) is reserved for box track or walls
            // Box track is roughly along i = j.
            // We keep a buffer of walls.
            // Reserved: j >= i - 1 && j <= i + 2
            if (j >= i - 1 && j <= i + 2) continue; // Keep walls/track
            
            // Upper Triangle (E-side)
            if (j > i + 2) {
                // Determine maze pattern
                // Serpentine along rows
                bool carve = false;
                if (i % 2 == 0) { // Even rows: Left to Right
                    if (j < M - 1) carve = true;
                    if (j == M - 1 && i < N - 3) carve = true; // Drop down at end, but check bounds
                } else { // Odd rows: Right to Left
                    if (j > i + 3) carve = true;
                    if (j == i + 3 && i < N - 3) carve = true; // Drop down
                }
                
                // Connection to track (E-Rail)
                // The cells (k, k+3) are adjacent to box track walls (k, k+2).
                // We need to punch holes to access the box.
                // Access points for DOWN push are (k-1, k+1).
                // (k-1, k+1) is in the "Reserved" zone.
                // We need to carve it and connect to (k-1, k+3) or similar.
                
                if (carve) grid[i][j] = '.';
            }
            
            // Lower Triangle (S-side)
            if (i > j + 2) { // j < i - 2
                // Serpentine along cols to vary
                bool carve = false;
                if (j % 2 == 0) { // Even cols: Top to Bottom
                    if (i < N - 1) carve = true;
                    if (i == N - 1 && j < M - 3) carve = true; // Move right
                } else {
                    if (i > j + 3) carve = true;
                    if (i == j + 3 && j < M - 3) carve = true; // Move right
                }
                if (carve) grid[i][j] = '.';
            }
        }
    }
    
    // Now connect E-Rail to Upper Maze
    // E-Rail access points are (k-1, k+1) for k roughly along path.
    // These need to connect to Upper Maze (k-1, k+3).
    // We simply open (k-1, k+2).
    // Be careful not to merge with S-side or Track.
    // (k-1, k+2) is strictly E-side.
    for (int k = 3; k < 44; k++) {
        // Only open if needed for a Down push.
        // Down push happens at (k, k) -> (k+1, k). No.
        // Path: (2,2)->(2,3)->(3,3)...
        // Down push is from (2,3) to (3,3).
        // Target box: (3,3). Player at (2,3) or (2,4).
        // Wait, box at (2,3) [rows 2,3 cols 3,4].
        // To push Down, Player at (1,3) or (1,4).
        // (1,3) is (k-1, k+1) type.
        // We need to connect (1,3) to Upper Maze.
        // (1,3) is adj to (1,4) which is adj to (1,5) (Maze).
        // So carve (1,3) and (1,4).
        
        // General: Box at (r, c). Push Down. Player at (r-1, c) or (r-1, c+1).
        // In our path, Down push occurs at r=k, c=k+1.
        // Box at (k, k+1). Player at (k-1, k+1) or (k-1, k+2).
        // We open (k-1, k+1) and (k-1, k+2).
        // Be careful: (k-1, k+1) might be wall of previous step?
        // Box previous was (k, k). Occupied (k, k+1).
        // (k-1, k+1) is outside box.
        
        int r = k; 
        int c = k+1; 
        // We iterate k covering the steps.
        // Actually path contains exact coords.
    }
    
    // Connect access points
    for (size_t i = 1; i < path.size(); ++i) {
        int pr = path[i-1].first;
        int pc = path[i-1].second;
        int cr = path[i].first;
        int cc = path[i].second;
        
        if (cr > pr) { // Move Down
            // Player needs to be at (pr-1, pc) or (pr-1, pc+1).
            // Connect these to E-Maze.
            // E-Maze starts at col pc+2 roughly.
            if (pr-1 >= 0) {
                grid[pr-1][pc] = '.';
                grid[pr-1][pc+1] = '.';
                // Connect to right
                if (pc+2 < M) grid[pr-1][pc+2] = '.';
            }
        } else { // Move Right
            // Player needs to be at (cr, cc-1) or (cr+1, cc-1).
            // Connect to S-Maze.
            // S-Maze starts at row cr+2 roughly.
            // Need to connect (cr+1, cc-1) downwards.
            if (cc-1 >= 0) {
                grid[cr][cc-1] = '.';
                grid[cr+1][cc-1] = '.';
                // Connect down
                if (cr+2 < N) grid[cr+2][cc-1] = '.';
            }
        }
    }
    
    // Connect Upper Maze to Lower Maze via perimeter tunnel
    // Upper Maze ends roughly at Bottom-Right or Top-Right depending on parity.
    // Our Upper Maze gen: Even rows go Right, Odd go Left.
    // Last row is N-1? No, we stopped at diagonal.
    // Let's connect (0, M-1) to (N-1, M-1) along right edge, then to (N-1, 0) along bottom?
    // Upper Maze fills top-right.
    // Let's make a vertical corridor at M-1 connecting all even rows.
    for (int i = 0; i < N; ++i) grid[i][M-1] = '.';
    // And bottom row corridor
    for (int j = 0; j < M; ++j) grid[N-1][j] = '.';
    // And left col corridor? No, S-Maze connects to bottom.
    // S-Maze (Lower Left) even cols go Down.
    // Ends at bottom.
    // So Bottom Corridor connects S-Maze ends to Right Corridor.
    // Right Corridor connects to Upper Maze ends.
    // Check connectivity:
    // S-Rail -> S-Maze -> Bottom Corridor -> Right Corridor -> Upper Maze -> E-Rail.
    // This looks valid.
    
    // Place Player
    // First move is Right from (2,2) to (2,3).
    // Player needs to be at (2,1).
    grid[2][1] = 'P';
    
    // Place Box
    // 2x2 at (2,2).
    grid[2][2] = 'B'; grid[2][3] = 'B';
    grid[3][2] = 'B'; grid[3][3] = 'B';
    
    // Place Storage
    // Last path pos.
    int last_r = path.back().first;
    int last_c = path.back().second;
    grid[last_r][last_c] = 'S'; grid[last_r][last_c+1] = 'S';
    grid[last_r+1][last_c] = 'S'; grid[last_r+1][last_c+1] = 'S';
    
    // Output
    cout << N << " " << M << endl;
    for (const string& row : grid) {
        cout << row << endl;
    }
    
    return 0;
}