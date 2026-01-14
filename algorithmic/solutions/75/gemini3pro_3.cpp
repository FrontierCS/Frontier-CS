#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    char c1, c2; // c1 = background, c2 = island
    int M; // Number of islands of C2
    int K; // Number of holes of C1 inside C2 islands

    // We choose the background color to be the one with the smaller cost coefficient
    // to minimize the total cost (since background typically uses more tiles).
    // If x < y, Black (@) is cheaper -> Background = @
    // If x >= y, White (.) is cheaper -> Background = .
    
    if (x < y) {
        c1 = '@';
        c2 = '.';
        // We need 'w' white components (islands).
        // We need 'b' black components. 
        // Background counts as 1 black component.
        // We need b - 1 additional black components (holes inside white islands).
        M = w;
        K = b - 1;
    } else {
        c1 = '.';
        c2 = '@';
        // We need 'b' black components (islands).
        // We need 'w' white components.
        // Background counts as 1 white component.
        // We need w - 1 additional white components (holes inside black islands).
        M = b;
        K = w - 1;
    }

    vector<string> grid;

    if (K == 0) {
        // Case A: No holes needed. We just need M simple islands.
        // A grid of height 2 is sufficient.
        // Row 0 contains the islands separated by background.
        // Row 1 is full background to keep the background connected.
        // Pattern: [Separator] [Island] [Separator] [Island] ...
        
        string r0 = "", r1 = "";
        
        // Initial separator
        r0 += c1;
        r1 += c1;
        
        for (int i = 0; i < M; ++i) {
            r0 += c2; // Island
            r1 += c1; // Background
            
            r0 += c1; // Separator
            r1 += c1; // Background
        }
        grid.push_back(r0);
        grid.push_back(r1);
    } else {
        // Case B: We need K holes.
        // We construct 1 "Complex Island" that contains all K holes, 
        // and M-1 "Simple Islands".
        // A grid of height 4 is used.
        // Row 3 is full background for connectivity.
        // Rows 0-2 contain the islands.
        
        string r0 = "", r1 = "", r2 = "", r3 = "";
        
        // Initial separator column
        r0 += c1; r1 += c1; r2 += c1; r3 += c1;
        
        // 1. Complex Island containing K holes
        // This island spans 3 rows (0, 1, 2).
        // Row 1 contains alternating C2 and C1. The C1s are the holes.
        // Width required: 2*K + 1
        for (int k = 0; k < 2 * K + 1; ++k) {
            r0 += c2;
            if (k % 2 == 0) r1 += c2; else r1 += c1; // C1 here is a hole
            r2 += c2;
            r3 += c1;
        }
        
        // Separator column
        r0 += c1; r1 += c1; r2 += c1; r3 += c1;
        
        // 2. Remaining M-1 simple islands
        for (int i = 0; i < M - 1; ++i) {
            // Simple island just needs to be an isolated C2.
            // We place it in Row 1, surrounded by C1 in R0, R2 and separators.
            r0 += c1;
            r1 += c2;
            r2 += c1;
            r3 += c1;
            
            // Separator column
            r0 += c1; r1 += c1; r2 += c1; r3 += c1;
        }
        
        grid.push_back(r0);
        grid.push_back(r1);
        grid.push_back(r2);
        grid.push_back(r3);
    }

    cout << grid.size() << " " << grid[0].size() << "\n";
    for (const string& row : grid) {
        cout << row << "\n";
    }

    return 0;
}