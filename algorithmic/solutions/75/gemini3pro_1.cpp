#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    if (cin >> b >> w >> x >> y) {
        // We construct the grid by splitting it into a top part (Black background)
        // and a bottom part (White background).
        // The top part will contain w-1 white islands.
        // The bottom part will contain b-1 black islands.
        // The interface between top (Black) and bottom (White) ensures the backgrounds 
        // are single connected components.
        
        // Calculate the minimum width required to fit the islands in one row.
        // Pattern for islands: @ . @ . @ (Islands at odd positions)
        // Length needed: 2 * islands + 1.
        int req_top = (w == 1) ? 1 : (2 * (w - 1) + 1);
        int req_bot = (b == 1) ? 1 : (2 * (b - 1) + 1);
        int c = max(req_top, req_bot);

        vector<string> grid;

        // Construct Top Part (Black background, White islands)
        if (w > 1) {
            // Row 1: Contains islands separated by background color
            string row = "";
            for (int i = 0; i < w - 1; ++i) {
                row += "@.";
            }
            row += "@";
            // Pad the rest of the row with background color
            while ((int)row.length() < c) row += "@";
            grid.push_back(row);
            
            // Row 2: "Spine" row, fully background color to connect all background pieces
            grid.push_back(string(c, '@'));
        } else {
            // If only 1 white component needed, it is provided by the bottom part's background.
            // We just need the black background here.
            grid.push_back(string(c, '@'));
        }

        // Construct Bottom Part (White background, Black islands)
        if (b > 1) {
            // Row 3: "Spine" row, fully background color
            grid.push_back(string(c, '.'));
            
            // Row 4: Contains islands
            string row = "";
            for (int i = 0; i < b - 1; ++i) {
                row += ".@";
            }
            row += ".";
            while ((int)row.length() < c) row += ".";
            grid.push_back(row);
        } else {
            // If only 1 black component needed, it is provided by the top part's background.
            // We just need the white background here.
            grid.push_back(string(c, '.'));
        }

        // Output results
        cout << grid.size() << " " << c << "\n";
        for (const string& s : grid) {
            cout << s << "\n";
        }
    }
    return 0;
}